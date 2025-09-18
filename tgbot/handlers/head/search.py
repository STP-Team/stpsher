import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from infrastructure.database.repo.KPI.requests import KPIRequestsRepo
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import HeadFilter
from tgbot.handlers.user.schedule.main import schedule_service
from tgbot.keyboards.common.search import (
    HeadUserStatusChange,
    HeadUserStatusSelect,
    ScheduleNavigation,
    SearchUserResult,
    ViewUserKPI,
    ViewUserSchedule,
    head_user_status_select_kb,
    search_back_kb,
    search_results_kb,
    user_detail_kb,
    user_schedule_with_month_kb,
)
from tgbot.keyboards.mip.search import get_month_name_by_index
from tgbot.keyboards.mip.search_kpi import search_user_kpi_kb
from tgbot.keyboards.user.main import MainMenu
from tgbot.misc.states.head.search import HeadSearchEmployee
from tgbot.services.salary import SalaryFormatter
from tgbot.services.search import SearchService

head_search_router = Router()
head_search_router.message.filter(F.chat.type == "private", HeadFilter())
head_search_router.callback_query.filter(F.message.chat.type == "private", HeadFilter())

logger = logging.getLogger(__name__)

# Константы для пагинации
USERS_PER_PAGE = 10


@head_search_router.callback_query(MainMenu.filter(F.menu == "head_search"))
async def head_search_start(callback: CallbackQuery, state: FSMContext):
    """Начать поиск сотрудников для руководителя"""
    bot_message = await callback.message.edit_text(
        """<b>🔍 Поиск сотрудника</b>

Введи часть имени, фамилии или полное ФИО сотрудника:

<i>Например: Иванов, Иван, Иванов И, Иванов Иван и т.д.</i>""",
        reply_markup=search_back_kb(context="head"),
    )

    await state.update_data(bot_message_id=bot_message.message_id)
    await state.set_state(HeadSearchEmployee.waiting_search_query)


@head_search_router.message(HeadSearchEmployee.waiting_search_query)
async def process_head_search_query(
    message: Message, state: FSMContext, stp_repo: MainRequestsRepo
):
    """Обработка поискового запроса от руководителя"""
    search_query = message.text.strip()
    state_data = await state.get_data()
    bot_message_id = state_data.get("bot_message_id")

    # Удаляем сообщение пользователя
    await message.delete()

    if not search_query or len(search_query) < 2:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text="""<b>🔍 Поиск сотрудника</b>

❌ Поисковый запрос слишком короткий (минимум 2 символа)

Введи часть имени, фамилии или полное ФИО сотрудника:

<i>Например: Иванов, Иван, Иванов И, Иванов Иван и т.д.</i>""",
            reply_markup=search_back_kb(context="head"),
        )
        return

    try:
        # Поиск пользователей по частичному совпадению ФИО
        found_users = await stp_repo.employee.get_users_by_fio_parts(
            search_query, limit=50
        )

        if not found_users:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=bot_message_id,
                text=f"""<b>🔍 Поиск сотрудника</b>

❌ По запросу "<code>{search_query}</code>" ничего не найдено

Попробуй другой запрос или проверь правильность написания

<i>Например: Иванов, Иван, Иванов И, Иванов Иван и т.д.</i>""",
                reply_markup=search_back_kb(context="head"),
            )
            return

        # Сортировка результатов (сначала точные совпадения)
        sorted_users = sorted(
            found_users,
            key=lambda u: (
                # Сначала полные совпадения
                search_query.lower() not in u.fullname.lower(),
                # Потом по алфавиту
                u.fullname,
            ),
        )

        # Пагинация результатов
        total_found = len(sorted_users)
        total_pages = (total_found + USERS_PER_PAGE - 1) // USERS_PER_PAGE
        page_users = sorted_users[:USERS_PER_PAGE]

        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text=f"""<b>🔍 Результаты поиска</b>

По запросу "<code>{search_query}</code>" найдено: {total_found} сотрудников
Страница 1 из {total_pages}""",
            reply_markup=search_results_kb(
                page_users,
                1,
                total_pages,
                "search_results",
                context="head",
                back_callback="main",
            ),
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при поиске пользователей: {e}")
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text="""<b>🔍 Поиск сотрудника</b>

❌ Произошла ошибка при поиске. Попробуй позже

<i>Например: Иванов, Иван, Иванов И, Иванов Иван и т.д.</i>""",
            reply_markup=search_back_kb(context="head"),
        )


@head_search_router.callback_query(SearchUserResult.filter(F.context == "head"))
async def show_head_user_details(
    callback: CallbackQuery, callback_data: SearchUserResult, stp_repo: MainRequestsRepo
):
    """Показать детальную информацию о найденном пользователе для руководителя"""
    user_id = callback_data.user_id
    return_to = callback_data.return_to
    head_id = callback_data.head_id

    try:
        user = await stp_repo.employee.get_user(user_id=user_id)
        user_head = (
            await stp_repo.employee.get_user(fullname=user.head) if user.head else None
        )

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Получаем статистику пользователя
        stats = await SearchService.get_user_statistics(user_id, stp_repo)

        # Формирование информации о пользователе
        user_info = SearchService.format_user_info_base(user, user_head, stats)

        # Дополнительная информация для руководителей
        if user.role == 2:  # Руководитель
            group_stats = await SearchService.get_group_statistics(
                user.fullname, stp_repo
            )
            user_info += SearchService.format_head_group_info(user, group_stats)

        # Определяем параметры клавиатуры для руководителей
        is_head = user.role == 2  # Руководитель
        head_user_id = user.user_id if is_head else 0

        # Получаем информацию о текущем руководителе
        current_head = await stp_repo.employee.get_user(user_id=callback.from_user.id)

        # Определяем, может ли руководитель изменять статус этого пользователя
        # Руководитель может изменять статус только своих подчиненных
        can_edit_status = (
            current_head
            and user.head
            and current_head.fullname == user.head
            and user.role in [1, 3]  # Только специалисты и дежурные
        )

        await callback.message.edit_text(
            user_info,
            reply_markup=user_detail_kb(
                user_id,
                return_to,
                head_id,
                context="head",
                show_edit_buttons=can_edit_status,  # Показываем кнопки изменения статуса для подчиненных
                is_head=is_head,
                head_user_id=head_user_id,
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка при получении информации о пользователе: {e}")
        await callback.answer("❌ Ошибка при получении данных", show_alert=True)


@head_search_router.callback_query(ViewUserSchedule.filter(F.context == "head"))
async def view_head_user_schedule(
    callback: CallbackQuery,
    callback_data: ViewUserSchedule,
    stp_repo: MainRequestsRepo,
):
    """Просмотр расписания пользователя для руководителя"""
    user_id = callback_data.user_id
    return_to = callback_data.return_to
    head_id = callback_data.head_id
    requested_month_idx = callback_data.month_idx

    try:
        # Получаем пользователя
        user = await stp_repo.employee.get_user(user_id=user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Определяем месяц для отображения
        if requested_month_idx > 0:
            current_month = get_month_name_by_index(requested_month_idx)
        else:
            current_month = schedule_service.get_current_month()

        try:
            # Получаем расписание пользователя (компактный формат) с дежурствами
            schedule_response = await schedule_service.get_user_schedule_response(
                user=user, month=current_month, compact=True, stp_repo=stp_repo
            )

            await callback.message.edit_text(
                f"""<b>📅 График сотрудника</b>

<b>ФИО:</b> <a href='t.me/{user.username}'>{user.fullname}</a>
<b>Подразделение:</b> {user.position or "Не указано"} {user.division or "Не указано"}

<blockquote>{schedule_response}</blockquote>""",
                reply_markup=user_schedule_with_month_kb(
                    user_id=user_id,
                    current_month=current_month,
                    return_to=return_to,
                    head_id=head_id,
                    is_detailed=False,
                    context="head",
                ),
            )

        except Exception as schedule_error:
            # Если не удалось получить расписание, показываем ошибку
            error_message = "❌ График для данного сотрудника не найдено"
            if "не найден" in str(schedule_error).lower():
                error_message = f"❌ Сотрудник {user.fullname} не найден в графике"
            elif "файл" in str(schedule_error).lower():
                error_message = "❌ Файл графика недоступен"

            await callback.message.edit_text(
                f"""<b>📅 График сотрудника</b>

<b>ФИО:</b> <a href='t.me/{user.username}'>{user.fullname}</a>
<b>Подразделение:</b> {user.position or "Не указано"} {user.division or "Не указано"}

{error_message}

<i>Возможно, сотрудник не включен в текущий график или файл недоступен.</i>""",
                reply_markup=user_schedule_with_month_kb(
                    user_id=user_id,
                    current_month=current_month,
                    return_to=return_to,
                    head_id=head_id,
                    is_detailed=False,
                    context="head",
                ),
            )

    except Exception as e:
        logger.error(f"Ошибка при получении расписания пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка при получении расписания", show_alert=True)


@head_search_router.callback_query(ScheduleNavigation.filter(F.context == "head"))
async def navigate_head_user_schedule(
    callback: CallbackQuery,
    callback_data: ScheduleNavigation,
    stp_repo: MainRequestsRepo,
):
    """Навигация по месяцам в расписании пользователя для руководителя"""
    user_id = callback_data.user_id
    action = callback_data.action
    month_idx = callback_data.month_idx
    return_to = callback_data.return_to
    head_id = callback_data.head_id

    try:
        # Получаем пользователя
        user = await stp_repo.employee.get_user(user_id=user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Определяем компактность вывода
        compact = action not in ["detailed"]

        # Преобразуем индекс месяца в название
        month_to_display = get_month_name_by_index(month_idx)

        try:
            # Получаем расписание пользователя с дежурствами
            schedule_response = await schedule_service.get_user_schedule_response(
                user=user, month=month_to_display, compact=compact, stp_repo=stp_repo
            )

            await callback.message.edit_text(
                f"""<b>📅 График сотрудника</b>

<b>ФИО:</b> <a href='t.me/{user.username}'>{user.fullname}</a>
<b>Подразделение:</b> {user.position or "Не указано"} {user.division or "Не указано"}

<blockquote>{schedule_response}</blockquote>""",
                reply_markup=user_schedule_with_month_kb(
                    user_id=user_id,
                    current_month=month_to_display,
                    return_to=return_to,
                    head_id=head_id,
                    is_detailed=not compact,
                    context="head",
                ),
            )

        except Exception as schedule_error:
            # Если не удалось получить расписание, показываем ошибку
            error_message = "❌ График для данного сотрудника не найдено"
            if "не найден" in str(schedule_error).lower():
                error_message = f"❌ Сотрудник {user.fullname} не найден в графике"
            elif "файл" in str(schedule_error).lower():
                error_message = "❌ Файл графика недоступен"

            await callback.message.edit_text(
                f"""<b>📅 График сотрудника</b>

<b>ФИО:</b> <a href='t.me/{user.username}'>{user.fullname}</a>
<b>Подразделение:</b> {user.position or "Не указано"} {user.division or "Не указано"}

{error_message}

<i>Возможно, сотрудник не включен в текущий график или файл недоступен.</i>""",
                reply_markup=user_schedule_with_month_kb(
                    user_id=user_id,
                    current_month=month_to_display,
                    return_to=return_to,
                    head_id=head_id,
                    is_detailed=not compact,
                    context="head",
                ),
            )

    except Exception as e:
        logger.error(f"Ошибка при навигации по расписанию пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка при получении расписания", show_alert=True)


@head_search_router.callback_query(ViewUserKPI.filter(F.context == "head"))
async def view_head_user_kpi(
    callback: CallbackQuery,
    callback_data: ViewUserKPI,
    stp_repo: MainRequestsRepo,
    kpi_repo: KPIRequestsRepo,
):
    """Просмотр KPI пользователя для руководителя"""
    user_id = callback_data.user_id
    return_to = callback_data.return_to
    head_id = callback_data.head_id

    try:
        # Получаем пользователя
        user = await stp_repo.employee.get_user(user_id=user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Получаем KPI данные пользователя
        try:
            premium = await kpi_repo.spec_premium.get_premium(fullname=user.fullname)

            if premium is None:
                message_text = f"""📊 <b>KPI: {user.fullname}</b>

❌ <b>Данные KPI не найдены</b>

Показатели эффективности для этого сотрудника отсутствуют в системе или не загружены.

<i>Обратись к администратору для проверки данных</i>"""

                await callback.message.edit_text(
                    message_text,
                    reply_markup=search_user_kpi_kb(
                        user_id, return_to, head_id, "main", context="head"
                    ),
                )
                return

            # Формируем сообщение с основными показателями
            message_text = f"""🌟 <b>Показатели</b>

<b>ФИО:</b> <a href="https://t.me/{user.username}">{user.fullname}</a>
<b>Подразделение:</b> {user.position or "Не указано"} {user.division or "Не указано"}

📊 <b>Оценка клиента - {SalaryFormatter.format_percentage(premium.csi_premium)}</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.csi)}
План: {SalaryFormatter.format_value(premium.csi_normative)}</blockquote>

🎯 <b>Отклик</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.csi_response)}
План: {SalaryFormatter.format_value(round(premium.csi_response_normative)) if premium.csi_response_normative else "—"}</blockquote>

🔧 <b>FLR - {SalaryFormatter.format_percentage(premium.flr_premium)}</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.flr)}
План: {SalaryFormatter.format_value(premium.flr_normative)}</blockquote>

⚖️ <b>ГОК - {SalaryFormatter.format_percentage(premium.gok_premium)}</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.gok)}
План: {SalaryFormatter.format_value(premium.gok_normative)}</blockquote>

🎯 <b>Цель - {SalaryFormatter.format_percentage(premium.target_premium)}</b>
<blockquote>Тип: {premium.target_type or "—"}
Факт: {SalaryFormatter.format_value(premium.target)}
План: {SalaryFormatter.format_value(round(premium.target_goal_first)) if premium.target_goal_first else "—"} / {SalaryFormatter.format_value(round(premium.target_goal_second)) if premium.target_goal_second else "—"}</blockquote>

💼 <b>Дополнительно</b>
<blockquote>Дисциплина: {SalaryFormatter.format_percentage(premium.discipline_premium)}
Тестирование: {SalaryFormatter.format_percentage(premium.tests_premium)}
Благодарности: {SalaryFormatter.format_percentage(premium.thanks_premium)}
Наставничество: {SalaryFormatter.format_percentage(premium.tutors_premium)}
Ручная правка: {SalaryFormatter.format_percentage(premium.head_adjust_premium)}</blockquote>

💰 <b>Итого:</b>
<b>Общая премия: {SalaryFormatter.format_percentage(premium.total_premium)}</b>

{"📈 Всего чатов: " + SalaryFormatter.format_value(premium.contacts_count) if user.division == "НЦК" else "📈 Всего звонков: " + SalaryFormatter.format_value(premium.contacts_count)}
{"⏰ Задержка: " + SalaryFormatter.format_value(premium.delay, " сек") if user.division != "НЦК" else ""}

<i>Выгружено: {premium.updated_at.strftime("%d.%m.%y %H:%M") if premium.updated_at else "—"}</i>"""

        except Exception as e:
            logger.error(f"Ошибка при получении KPI для {user.fullname}: {e}")

            # Проверяем, является ли ошибка отсутствием таблицы
            error_str = str(e)
            if "Table" in error_str and "doesn't exist" in error_str:
                message_text = f"""📊 <b>KPI: {user.fullname}</b>

⚠️ <b>Система KPI недоступна</b>

Таблица показателей эффективности не найдена в базе данных.

<i>Обратись к администратору для настройки системы KPI.</i>"""
            else:
                message_text = f"""📊 <b>KPI: {user.fullname}</b>

❌ <b>Ошибка загрузки данных</b>

Произошла ошибка при получении показателей эффективности.

<i>Попробуй позже или обратись к администратору для проверки данных</i>"""

        await callback.message.edit_text(
            message_text,
            reply_markup=search_user_kpi_kb(
                user_id, return_to, head_id, "main", context="head"
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка при получении KPI пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка при получении KPI", show_alert=True)


@head_search_router.callback_query(HeadUserStatusSelect.filter())
async def show_head_user_status_select(
    callback: CallbackQuery,
    callback_data: HeadUserStatusSelect,
    stp_repo: MainRequestsRepo,
):
    """Обработчик показа меню выбора статуса пользователя"""
    user_id = callback_data.user_id
    return_to = callback_data.return_to
    head_id = callback_data.head_id
    context = callback_data.context

    try:
        # Получаем пользователя
        user = await stp_repo.employee.get_user(user_id=user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Получаем информацию о текущем руководителе
        current_head = await stp_repo.employee.get_user(user_id=callback.from_user.id)

        # Проверяем, что руководитель может изменять статус этого пользователя
        if not (
            current_head
            and user.head
            and current_head.fullname == user.head
            and user.role in [1, 3]
        ):
            await callback.answer(
                "❌ Ты можешь изменять статус только своих подчиненных", show_alert=True
            )
            return

        # Формируем информацию об участнике
        message_text = f"""⚙️ <b>Изменение статуса</b>

<b>ФИО:</b> <a href="https://t.me/{user.username}">{user.fullname}</a>
<b>Подразделение:</b> {user.position or "Не указано"} {user.division or ""}

<i>Выбери новый статус для сотрудника:</i>"""

        await callback.message.edit_text(
            message_text,
            reply_markup=head_user_status_select_kb(
                user_id=user_id,
                return_to=return_to,
                head_id=head_id,
                context=context,
                current_role=user.role,
                is_trainee=user.is_trainee,
            ),
        )

    except Exception as e:
        logger.error(
            f"Ошибка при отображении выбора статуса пользователя {user_id}: {e}"
        )
        await callback.answer("❌ Ошибка при отображении меню", show_alert=True)


@head_search_router.callback_query(HeadUserStatusChange.filter())
async def change_head_user_status(
    callback: CallbackQuery,
    callback_data: HeadUserStatusChange,
    stp_repo: MainRequestsRepo,
):
    """Обработчик изменения статуса пользователя (стажер/дежурный)"""
    user_id = callback_data.user_id
    status_type = callback_data.status_type
    return_to = callback_data.return_to
    head_id = callback_data.head_id
    context = callback_data.context

    try:
        # Получаем пользователя
        user = await stp_repo.employee.get_user(user_id=user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Получаем информацию о текущем руководителе
        current_head = await stp_repo.employee.get_user(user_id=callback.from_user.id)

        # Проверяем, что руководитель может изменять статус этого пользователя
        if not (current_head and user.head and current_head.fullname == user.head):
            await callback.answer(
                "❌ Ты можешь изменять статус только своих подчиненных", show_alert=True
            )
            return

        # Проверяем, что роль может быть изменена
        if user.role not in [1, 3] and status_type == "duty":
            await callback.answer(
                "❌ Уровень доступа этого пользователя нельзя изменить", show_alert=True
            )
            return

        notification_text = ""
        changes_made = False

        if status_type == "trainee":
            # Переключаем статус стажера
            new_trainee_status = not user.is_trainee
            await stp_repo.employee.update_user(
                user_id=user.user_id, is_trainee=new_trainee_status
            )

            status_text = "стажер" if new_trainee_status else "не стажер"
            notification_text = f"Статус стажера изменен: {status_text}"
            changes_made = True

            logger.info(
                f"[Руководитель] - [Поиск] {callback.from_user.username} ({callback.from_user.id}) изменил статус стажера пользователя {user_id}: {new_trainee_status}"
            )

        elif status_type == "duty":
            # Определяем старую и новую роль ДО изменения
            old_role_name = "Дежурный" if user.role == 3 else "Специалист"
            new_role = 1 if user.role == 3 else 3
            new_role_name = "Специалист" if new_role == 1 else "Дежурный"

            # Переключаем роль дежурного
            await stp_repo.employee.update_user(user_id=user.user_id, role=new_role)

            notification_text = f"Роль изменена: {old_role_name} → {new_role_name}"
            changes_made = True

            # Отправляем уведомление пользователю о смене роли (только если он авторизован)
            if user.user_id:
                try:
                    await callback.bot.send_message(
                        chat_id=user.user_id,
                        text=f"""<b>🔔 Изменение роли</b>

Уровень был изменен: {old_role_name} → {new_role_name}

<i>Изменения могут повлиять на доступные функции бота</i>""",
                    )
                except TelegramBadRequest as e:
                    logger.error(
                        f"Не удалось отправить уведомление пользователю {user.user_id}: {e}"
                    )

            logger.info(
                f"[Руководитель] - [Поиск] {callback.from_user.username} ({callback.from_user.id}) изменил роль пользователя {user_id}: {old_role_name} → {new_role_name}"
            )

        if changes_made:
            await callback.answer(notification_text)

            # Обновляем меню выбора статуса с обновленными данными
            await show_head_user_status_select(
                callback,
                HeadUserStatusSelect(
                    user_id=user_id,
                    return_to=return_to,
                    head_id=head_id,
                    context=context,
                ),
                stp_repo,
            )
        else:
            await callback.answer("❌ Неизвестный тип статуса", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка при изменении статуса пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка при изменении статуса", show_alert=True)

import logging
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models import Employee
from infrastructure.database.repo.KPI.requests import KPIRequestsRepo
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.handlers.user.schedule.main import schedule_service
from tgbot.keyboards.mip.search import (
    EditUserMenu,
    SelectUserRole,
    edit_user_back_kb,
    role_selection_kb,
)
from tgbot.keyboards.search.main import SearchMenu, search_main_kb
from tgbot.keyboards.search.search import (
    HeadUserCasinoToggle,
    HeadUserStatusChange,
    HeadUserStatusSelect,
    ScheduleNavigation,
    SearchFilterToggleMenu,
    SearchUserResult,
    ViewUserKPI,
    ViewUserSchedule,
    get_month_name_by_index,
    head_user_status_select_kb,
    search_back_kb,
    search_results_kb,
    search_user_kpi_kb,
    toggle_filter,
    user_detail_kb,
    user_schedule_with_month_kb,
)
from tgbot.keyboards.user.main import MainMenu
from tgbot.misc.dicts import roles
from tgbot.misc.helpers import get_role
from tgbot.misc.states.search import EditEmployee, SearchEmployee
from tgbot.services.salary import SalaryFormatter
from tgbot.services.search import SearchService

search_router = Router()

# Фильтры для роутера - обрабатываем запросы от МИП и руководителей
search_router.message.filter(F.chat.type == "private")
search_router.callback_query.filter(F.message.chat.type == "private")

logger = logging.getLogger(__name__)

# Константы для пагинации
USERS_PER_PAGE = 10


@search_router.callback_query(MainMenu.filter(F.menu == "search"))
async def search_main_menu(callback: CallbackQuery, state: FSMContext, user: Employee):
    await state.clear()

    # Определяем контекст в зависимости от роли пользователя
    if user.role == 10:  # root
        context = "root"
    elif user.role == 6:  # МИП
        context = "mip"
    elif user.role == 2:  # Руководитель
        context = "head"
    else:  # Обычные пользователи
        context = "user"

    await state.update_data(user_context=context)

    await callback.message.edit_text(
        """<b>🕵🏻 Поиск сотрудника</b>

<i>Выбери должность искомого человека или воспользуйся общим поиском</i>""",
        reply_markup=search_main_kb(),
    )


@search_router.callback_query(SearchMenu.filter())
async def search_menu_handler(
    callback: CallbackQuery,
    callback_data: SearchMenu,
    stp_repo: MainRequestsRepo,
    state: FSMContext,
    user: Employee,
):
    """Обработка меню поиска"""
    menu = callback_data.menu

    # Определяем контекст в зависимости от роли пользователя
    if user.role == 10:  # root
        context = "root"
    elif user.role == 6:  # МИП
        context = "mip"
    elif user.role == 2:  # Руководитель
        context = "head"
    else:  # Обычные пользователи
        context = "user"

    if menu == "specialists":
        await show_specialists(callback, callback_data, stp_repo, context)
    elif menu == "heads":
        await show_heads(callback, callback_data, stp_repo, context)
    elif menu == "start_search":
        await start_search(callback, context, state)


@search_router.callback_query(SearchFilterToggleMenu.filter())
async def handle_search_filter_toggle(
    callback: CallbackQuery,
    callback_data: SearchFilterToggleMenu,
    stp_repo: MainRequestsRepo,
    user: Employee,
):
    """Обработка переключения фильтров для поиска"""
    menu = callback_data.menu
    filter_name = callback_data.filter_name
    current_filters = callback_data.current_filters

    # Переключаем фильтр
    new_filters = toggle_filter(current_filters, filter_name)

    # Определяем контекст в зависимости от роли пользователя
    if user.role == 10:  # root
        context = "root"
    elif user.role == 6:  # МИП
        context = "mip"
    elif user.role == 2:  # Руководитель
        context = "head"
    else:  # Обычные пользователи
        context = "user"

    # Создаем новый SearchMenu с обновленными фильтрами и сбрасываем страницу на 1
    new_callback_data = SearchMenu(menu=menu, page=1, filters=new_filters)

    # Вызываем соответствующую функцию в зависимости от меню
    if menu == "specialists":
        await show_specialists(callback, new_callback_data, stp_repo, context)
    elif menu == "heads":
        await show_heads(callback, new_callback_data, stp_repo, context)


async def show_specialists(
    callback: CallbackQuery,
    callback_data: SearchMenu,
    stp_repo: MainRequestsRepo,
    context: str,
):
    """Показать всех специалистов с пагинацией"""
    page = callback_data.page
    filters = callback_data.filters

    # Получаем всех пользователей и фильтруем специалистов
    all_users = await stp_repo.employee.get_users()
    if not all_users:
        await callback.answer("❌ Пользователи не найдены", show_alert=True)
        return

    specialists = SearchService.filter_users_by_type(all_users, "specialists")

    # Применяем фильтры по подразделениям
    if filters:
        active_filters = set(f.strip() for f in filters.split(",") if f.strip())
        if active_filters and active_filters != {"НЦК", "НТП1", "НТП2"}:
            specialists = [u for u in specialists if u.division in active_filters]

    if not specialists:
        await callback.answer("❌ Специалисты не найдены", show_alert=True)
        return

    # Сортировка по алфавиту
    specialists.sort(key=lambda u: u.fullname)

    # Пагинация
    total_users = len(specialists)
    total_pages = (total_users + USERS_PER_PAGE - 1) // USERS_PER_PAGE

    start_idx = (page - 1) * USERS_PER_PAGE
    end_idx = start_idx + USERS_PER_PAGE
    page_users = specialists[start_idx:end_idx]

    await callback.message.edit_text(
        f"""<b>👤 Специалисты</b>

Найдено специалистов: {total_users}
Страница {page} из {total_pages}""",
        reply_markup=search_results_kb(
            page_users,
            page,
            total_pages,
            "specialists",
            context=context,
            back_callback="search" if context == "mip" else "main",
            filters=filters,
        ),
    )


async def show_heads(
    callback: CallbackQuery,
    callback_data: SearchMenu,
    stp_repo: MainRequestsRepo,
    context: str,
):
    """Показать всех руководителей с пагинацией"""
    page = callback_data.page
    filters = callback_data.filters

    # Получаем всех пользователей и фильтруем руководителей
    all_users = await stp_repo.employee.get_users()
    if not all_users:
        await callback.answer("❌ Пользователи не найдены", show_alert=True)
        return

    heads = SearchService.filter_users_by_type(all_users, "heads")

    # Применяем фильтры по подразделениям
    if filters:
        active_filters = set(f.strip() for f in filters.split(",") if f.strip())
        if active_filters and active_filters != {"НЦК", "НТП1", "НТП2"}:
            heads = [u for u in heads if u.division in active_filters]

    if not heads:
        await callback.answer("❌ Руководители не найдены", show_alert=True)
        return

    # Сортировка по алфавиту
    heads.sort(key=lambda u: u.fullname)

    # Пагинация
    total_users = len(heads)
    total_pages = (total_users + USERS_PER_PAGE - 1) // USERS_PER_PAGE

    start_idx = (page - 1) * USERS_PER_PAGE
    end_idx = start_idx + USERS_PER_PAGE
    page_users = heads[start_idx:end_idx]

    await callback.message.edit_text(
        f"""<b>👑 Руководители</b>

Найдено руководителей: {total_users}""",
        reply_markup=search_results_kb(
            page_users,
            page,
            total_pages,
            "heads",
            context=context,
            back_callback="search" if context == "mip" else "main",
            filters=filters,
        ),
    )


async def start_search(callback: CallbackQuery, context: str, state: FSMContext):
    """Начать поиск по имени"""
    bot_message = await callback.message.edit_text(
        """<b>🕵🏻 Поиск сотрудника</b>

Введи часть имени, фамилии или полное ФИО сотрудника:

<i>Например: Иванов, Иван, Иванов И, Иванов Иван и т.д.</i>""",
        reply_markup=search_back_kb(context=context),
    )

    await state.update_data(bot_message_id=bot_message.message_id, context=context)
    await state.set_state(SearchEmployee.waiting_search_query)


@search_router.message(SearchEmployee.waiting_search_query)
async def process_search_query(
    message: Message, state: FSMContext, stp_repo: MainRequestsRepo
):
    """Обработка поискового запроса"""
    search_query = message.text.strip()
    state_data = await state.get_data()
    bot_message_id = state_data.get("bot_message_id")
    context = state_data.get("context", "mip")

    # Удаляем сообщение пользователя
    await message.delete()

    if not search_query or len(search_query) < 2:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text="""<b>🕵🏻 Поиск сотрудника</b>

❌ Поисковый запрос слишком короткий (минимум 2 символа)

Введи часть имени, фамилии или полное ФИО сотрудника:

<i>Например: Иванов, Иван, Иванов И, Иванов Иван и т.д.</i>""",
            reply_markup=search_back_kb(context=context),
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
                text=f"""<b>🕵🏻 Поиск сотрудника</b>

❌ По запросу "<code>{search_query}</code>" ничего не найдено

Попробуй другой запрос или проверь правильность написания

<i>Например: Иванов, Иван, Иванов И, Иванов Иван и т.д.</i>""",
                reply_markup=search_back_kb(context=context),
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

        back_callback = "search" if context == "mip" else "main"

        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text=f"""<b>🔍 Результаты поиска</b>

По запросу "<code>{search_query}</code>" найдено: {total_found} сотрудников""",
            reply_markup=search_results_kb(
                page_users,
                1,
                total_pages,
                "search_results",
                context=context,
                back_callback=back_callback,
                filters="НЦК,НТП1,НТП2",
            ),
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при поиске пользователей: {e}")
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text="""<b>🕵🏻 Поиск сотрудника</b>

❌ Произошла ошибка при поиске. Попробуй позже

<i>Например: Иванов, Иван, Иванов И, Иванов Иван и т.д.</i>""",
            reply_markup=search_back_kb(context=context),
        )


@search_router.callback_query(SearchUserResult.filter())
async def show_user_details(
    callback: CallbackQuery,
    callback_data: SearchUserResult,
    stp_repo: MainRequestsRepo,
    user: Employee,
):
    """Показать детальную информацию о найденном пользователе"""
    user_id = callback_data.user_id
    return_to = callback_data.return_to
    head_id = callback_data.head_id
    context = callback_data.context
    viewer_role = user.role  # Роль пользователя, который смотрит информацию

    try:
        target_user = await stp_repo.employee.get_user(user_id=user_id)
        user_head = (
            await stp_repo.employee.get_user(fullname=target_user.head)
            if target_user.head
            else None
        )

        if not target_user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Получаем статистику пользователя (только для роли 2 и выше)
        stats = None
        if viewer_role >= 2:
            stats = await SearchService.get_user_statistics(user_id, stp_repo)

        # Формирование информации о пользователе в зависимости от роли смотрящего
        user_info = SearchService.format_user_info_role_based(
            target_user, user_head, stats, viewer_role
        )

        # Дополнительная информация для руководителей (только для роли 2 и выше)
        if target_user.role == 2 and viewer_role >= 2:  # Руководитель
            group_stats = await SearchService.get_group_statistics(
                target_user.fullname, stp_repo
            )
            user_info += SearchService.format_head_group_info(group_stats)

        # Определяем возможности редактирования в зависимости от контекста и роли
        if context == "mip" and viewer_role >= 6:  # МИП может редактировать всех
            can_edit = target_user.role in [1, 2, 3]
        elif (
            context == "head" and viewer_role == 2
        ):  # Руководитель может редактировать только специалистов и дежурных
            can_edit = target_user.role in [1, 3]
        else:
            can_edit = False

        is_head = target_user.role == 2
        head_user_id = target_user.user_id if is_head else 0

        await callback.message.edit_text(
            user_info,
            reply_markup=user_detail_kb(
                target_user,
                return_to,
                head_id,
                context=context,
                show_edit_buttons=can_edit,
                is_head=is_head,
                head_user_id=head_user_id,
                viewer_role=viewer_role,
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка при получении информации о пользователе: {e}")
        await callback.answer("❌ Ошибка при получении данных", show_alert=True)


@search_router.callback_query(ViewUserSchedule.filter())
async def view_user_schedule(
    callback: CallbackQuery,
    callback_data: ViewUserSchedule,
    stp_repo: MainRequestsRepo,
):
    """Просмотр расписания пользователя"""
    user_id = callback_data.user_id
    return_to = callback_data.return_to
    head_id = callback_data.head_id
    requested_month_idx = callback_data.month_idx
    context = callback_data.context

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
                    context=context,
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
                    context=context,
                ),
            )

    except Exception as e:
        logger.error(f"Ошибка при получении расписания пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка при получении расписания", show_alert=True)


@search_router.callback_query(ScheduleNavigation.filter())
async def navigate_user_schedule(
    callback: CallbackQuery,
    callback_data: ScheduleNavigation,
    stp_repo: MainRequestsRepo,
):
    """Навигация по месяцам в расписании пользователя"""
    user_id = callback_data.user_id
    action = callback_data.action
    month_idx = callback_data.month_idx
    return_to = callback_data.return_to
    head_id = callback_data.head_id
    context = callback_data.context

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
                    context=context,
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
                    context=context,
                ),
            )

    except Exception as e:
        logger.error(f"Ошибка при навигации по расписанию пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка при получении расписания", show_alert=True)


@search_router.callback_query(ViewUserKPI.filter())
async def view_user_kpi(
    callback: CallbackQuery,
    callback_data: ViewUserKPI,
    stp_repo: MainRequestsRepo,
    kpi_repo: KPIRequestsRepo,
):
    """Просмотр KPI пользователя"""
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
                        user_id, return_to, head_id, "main", context=context
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

            message_text = f"""📊 <b>KPI: {user.fullname}</b>

❌ <b>Ошибка загрузки данных</b>

Произошла ошибка при получении показателей эффективности.

<i>Попробуй позже или обратись к администратору для проверки данных</i>"""

        await callback.message.edit_text(
            message_text,
            reply_markup=search_user_kpi_kb(
                user_id, return_to, head_id, "main", context=context
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка при получении KPI пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка при получении KPI", show_alert=True)


# Обработчики для руководителей
@search_router.callback_query(HeadUserStatusSelect.filter())
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

        # Проверяем, что руководитель может изменять статус этого пользователя
        if user.role not in [1, 3]:
            await callback.answer(
                "❌ Ты можешь изменять статус только специалистов и дежурных",
                show_alert=True,
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


@search_router.callback_query(HeadUserStatusChange.filter())
async def change_head_user_status(
    callback: CallbackQuery,
    callback_data: HeadUserStatusChange,
    stp_repo: MainRequestsRepo,
):
    """Обработчик изменения статуса пользователя (стажер/дежурный)"""
    from aiogram.exceptions import TelegramBadRequest

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

        # Проверяем, что руководитель может изменять статус этого пользователя
        if user.role not in [1, 3]:
            await callback.answer(
                "❌ Ты можешь изменять статус только специалистов и дежурных",
                show_alert=True,
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


@search_router.callback_query(HeadUserCasinoToggle.filter())
async def toggle_head_user_casino(
    callback: CallbackQuery,
    callback_data: HeadUserCasinoToggle,
    stp_repo: MainRequestsRepo,
    user: Employee,
):
    """Обработчик переключения доступа к казино для пользователя из поиска"""
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

        # Проверяем, что руководитель может изменять доступ к казино
        if user.role not in [1, 3]:
            await callback.answer(
                "❌ Доступ к казино можно изменять только для специалистов и дежурных",
                show_alert=True,
            )
            return

        # Переключаем доступ к казино
        new_casino_status = not user.is_casino_allowed
        await stp_repo.employee.update_user(
            user_id=user.user_id, is_casino_allowed=new_casino_status
        )

        status_text = "разрешен" if new_casino_status else "запрещен"
        await callback.answer(f"Доступ к казино {status_text}")

        logger.info(
            f"[Руководитель] - [Поиск] {callback.from_user.username} ({callback.from_user.id}) изменил доступ к казино пользователя {user_id}: {new_casino_status}"
        )

        # Обновляем информацию о пользователе
        await show_user_details(
            callback,
            SearchUserResult(
                user_id=user_id,
                return_to=return_to,
                head_id=head_id,
                context=context,
            ),
            stp_repo,
            user,
        )

    except Exception as e:
        logger.error(
            f"Ошибка при изменении доступа к казино пользователя {user_id}: {e}"
        )
        await callback.answer("❌ Ошибка при изменении доступа", show_alert=True)


# Обработчики для МИП (редактирование пользователей)
@search_router.callback_query(EditUserMenu.filter())
async def start_edit_user(
    callback: CallbackQuery,
    callback_data: EditUserMenu,
    state: FSMContext,
    stp_repo: MainRequestsRepo,
):
    """Начать редактирование данных пользователя (только для МИП)"""
    user_id = callback_data.user_id
    action = callback_data.action

    if action == "edit_fullname":
        # Получаем текущие данные пользователя
        user = await stp_repo.employee.get_user(user_id=user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        bot_message = await callback.message.edit_text(
            f"""<b>✏️ Изменение ФИО</b>

<b>Текущее ФИО:</b> {user.fullname}

Введи новое ФИО:

<i>Например: Иванов Иван Иванович</i>""",
            reply_markup=edit_user_back_kb(user_id),
        )

        await state.update_data(
            bot_message_id=bot_message.message_id,
            user_id=user_id,
            current_fullname=user.fullname,
        )
        await state.set_state(EditEmployee.waiting_new_fullname)

    elif action == "edit_role":
        # Получаем текущие данные пользователя
        user = await stp_repo.employee.get_user(user_id=user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        await callback.message.edit_text(
            f"""🛡️ <b>Изменение уровня доступа</b>

<b>Сотрудник:</b> <a href='t.me/{user.username}'>{user.fullname}</a>
<b>Текущий уровень доступа:</b> {get_role(user.role)["name"]}

Выбери новую уровень для пользователя:

<i>Пользователь получит уведомление об изменении</i>""",
            reply_markup=role_selection_kb(user_id, user.role),
        )


# Import statements moved from bottom for these keyboard functions


@search_router.message(EditEmployee.waiting_new_fullname)
async def process_edit_fullname(
    message: Message, state: FSMContext, stp_repo: MainRequestsRepo
):
    """Обработка изменения ФИО пользователя (только для МИП)"""

    new_fullname = message.text.strip()
    state_data = await state.get_data()
    bot_message_id = state_data.get("bot_message_id")
    user_id = state_data.get("user_id")
    current_fullname = state_data.get("current_fullname")

    # Удаляем сообщение пользователя
    await message.delete()

    # Валидация ФИО
    fullname_pattern = r"^[А-Яа-яЁё]+ [А-Яа-яЁё]+ [А-Яа-яЁё]+$"
    if not re.match(fullname_pattern, new_fullname):
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text=f"""<b>✏️ Изменение ФИО</b>

<b>Текущее ФИО:</b> {current_fullname}

❌ Неверный формат ФИО. Попробуй ещё раз:

<i>Например: Иванов Иван Иванович</i>""",
            reply_markup=edit_user_back_kb(user_id),
        )
        return

    try:
        # Обновляем ФИО в базе данных
        await stp_repo.employee.update_user(user_id=user_id, fullname=new_fullname)

        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text=f"""<b>✅ ФИО изменено</b>

<b>Было:</b> <code>{current_fullname}</code>
<b>Стало:</b> <code>{new_fullname}</code>

Изменения сохранены в базе данных.""",
            reply_markup=edit_user_back_kb(user_id),
        )

        await state.clear()
        logger.info(
            f"[МИП] - [Изменение ФИО] {message.from_user.username} ({message.from_user.id}) изменил ФИО пользователя {user_id}: {current_fullname} → {new_fullname}"
        )

    except Exception as e:
        logger.error(f"Ошибка при изменении ФИО пользователя {user_id}: {e}")
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text=f"""<b>✏️ Изменение ФИО</b>

❌ Произошла ошибка при сохранении. Попробуй позже

<b>Текущее ФИО:</b> {current_fullname}""",
            reply_markup=edit_user_back_kb(user_id),
        )


@search_router.callback_query(SelectUserRole.filter())
async def process_role_change(
    callback: CallbackQuery,
    callback_data: SelectUserRole,
    stp_repo: MainRequestsRepo,
    user: Employee,
):
    """Обработка изменения роли пользователя (только для МИП)"""
    user_id = callback_data.user_id
    new_role = callback_data.role

    try:
        # Получаем данные пользователя
        user = await stp_repo.employee.get_user(user_id=user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Проверяем, что роль действительно изменилась
        if user.role == new_role:
            await callback.answer("❌ Пользователь уже имеет эту роль", show_alert=True)
            return

        # Получаем названия ролей
        old_role_name = (
            roles[user.role]["name"]
            if user.role in roles
            else f"Неизвестный уровень ({user.role})"
        )
        new_role_name = (
            roles[new_role]["name"]
            if new_role in roles
            else f"Неизвестный уровень ({new_role})"
        )

        # Обновляем роль в базе данных
        await stp_repo.employee.update_user(user_id=user_id, role=new_role)

        # Отправляем уведомление пользователю о смене роли
        try:
            await callback.bot.send_message(
                chat_id=user_id,
                text=f"""<b>🔔 Изменение роли</b>

Уровень был изменен: {old_role_name} → {new_role_name}

<i>Изменения могут повлиять на доступные функции бота</i>""",
            )
        except Exception as notify_error:
            logger.error(
                f"Не удалось отправить уведомление пользователю {user_id}: {notify_error}"
            )

        logger.info(
            f"[МИП] - [Изменение роли] {callback.from_user.username} ({callback.from_user.id}) изменил роль пользователя {user_id}: {old_role_name} → {new_role_name}"
        )

        # Возвращаемся к информации о пользователе
        user_callback_data = SearchUserResult(user_id=user_id, context="mip")
        await show_user_details(callback, user_callback_data, stp_repo, user)

    except Exception as e:
        logger.error(f"Ошибка при изменении роли пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка при сохранении роли", show_alert=True)

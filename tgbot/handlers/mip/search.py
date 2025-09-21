import logging
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Message,
)

from infrastructure.database.models import Employee
from infrastructure.database.repo.KPI.requests import KPIRequestsRepo
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import MipFilter
from tgbot.handlers.user.schedule.main import schedule_service
from tgbot.keyboards.common.search import (
    ScheduleNavigation,
    SearchUserResult,
    ViewUserSchedule,
    search_back_kb,
    search_results_kb,
    user_detail_kb,
    user_schedule_with_month_kb,
)
from tgbot.keyboards.mip.search import (
    EditUserMenu,
    HeadGroupMembersMenuForSearch,
    HeadGroupMenu,
    HeadMemberActionMenuForSearch,
    HeadMemberDetailMenuForSearch,
    HeadMemberRoleChangeForSearch,
    SearchMemberScheduleMenu,
    SearchMemberScheduleNavigation,
    SearchMenu,
    SelectUserRole,
    edit_user_back_kb,
    get_month_name_by_index,
    head_group_members_kb_for_search,
    head_member_detail_kb_for_search,
    role_selection_kb,
    search_main_kb,
    search_member_schedule_kb,
)
from tgbot.keyboards.mip.search_kpi import (
    SearchMemberKPIMenu,
    SearchUserKPIMenu,
    search_member_kpi_kb,
    search_user_kpi_kb,
)
from tgbot.keyboards.user.main import MainMenu
from tgbot.misc.dicts import roles
from tgbot.misc.states.mip.search import EditEmployee, SearchEmployee
from tgbot.services.leveling import LevelingSystem
from tgbot.services.salary import KPICalculator, SalaryCalculator, SalaryFormatter
from tgbot.services.search import SearchService

mip_search_router = Router()
mip_search_router.message.filter(F.chat.type == "private", MipFilter())
mip_search_router.callback_query.filter(F.message.chat.type == "private", MipFilter())

logger = logging.getLogger(__name__)

# Константы для пагинации
USERS_PER_PAGE = 10


@mip_search_router.callback_query(MainMenu.filter(F.menu == "search"))
async def search_main_menu(callback: CallbackQuery, state: FSMContext):
    """Главное меню поиска сотрудников"""
    await state.clear()
    await callback.message.edit_text(
        """<b>🕵🏻 Поиск сотрудника</b>

<i>Выбери должность искомого человека или воспользуйся общим поиском</i>""",
        reply_markup=search_main_kb(),
    )


@mip_search_router.callback_query(SearchMenu.filter(F.menu == "specialists"))
async def show_specialists(
    callback: CallbackQuery, callback_data: SearchMenu, stp_repo: MainRequestsRepo
):
    """Показать всех специалистов с пагинацией"""
    page = callback_data.page

    # Получаем всех пользователей и фильтруем специалистов
    all_users = await stp_repo.employee.get_users()
    if not all_users:
        await callback.answer("❌ Пользователи не найдены", show_alert=True)
        return

    specialists = SearchService.filter_users_by_type(all_users, "specialists")

    if not specialists:
        await callback.answer("❌ Специалисты не найдены", show_alert=True)
        return

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
            context="mip",
            back_callback="search",
        ),
    )


@mip_search_router.callback_query(SearchMenu.filter(F.menu == "heads"))
async def show_heads(
    callback: CallbackQuery, callback_data: SearchMenu, stp_repo: MainRequestsRepo
):
    """Показать всех руководителей с пагинацией"""
    page = callback_data.page

    # Получаем всех пользователей и фильтруем руководителей
    all_users = await stp_repo.employee.get_users()
    if not all_users:
        await callback.answer("❌ Пользователи не найдены", show_alert=True)
        return

    heads = SearchService.filter_users_by_type(all_users, "heads")

    if not heads:
        await callback.answer("❌ Руководители не найдены", show_alert=True)
        return

    # Пагинация
    total_users = len(heads)
    total_pages = (total_users + USERS_PER_PAGE - 1) // USERS_PER_PAGE

    start_idx = (page - 1) * USERS_PER_PAGE
    end_idx = start_idx + USERS_PER_PAGE
    page_users = heads[start_idx:end_idx]

    await callback.message.edit_text(
        f"""<b>👑 Руководители</b>

Найдено руководителей: {total_users}
Страница {page} из {total_pages}

<i>💡 Нажми на руководителя, чтобы увидеть его группу</i>""",
        reply_markup=search_results_kb(
            page_users,
            page,
            total_pages,
            "heads",
            context="mip",
            back_callback="search",
        ),
    )


@mip_search_router.callback_query(SearchMenu.filter(F.menu == "start_search"))
async def start_search(callback: CallbackQuery, state: FSMContext):
    """Начать поиск по имени"""
    bot_message = await callback.message.edit_text(
        """<b>🔍 Поиск сотрудника</b>

Введи часть имени, фамилии или полное ФИО сотрудника:

<i>Например: Иванов, Иван, Иванов И, Иванов Иван и т.д.</i>""",
        reply_markup=search_back_kb(context="mip"),
    )

    await state.update_data(bot_message_id=bot_message.message_id)
    await state.set_state(SearchEmployee.waiting_search_query)


@mip_search_router.message(SearchEmployee.waiting_search_query)
async def process_search_query(
    message: Message, state: FSMContext, stp_repo: MainRequestsRepo
):
    """Обработка поискового запроса"""
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
            reply_markup=search_back_kb(context="mip"),
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
                reply_markup=search_back_kb(context="mip"),
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
                context="mip",
                back_callback="search",
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
            reply_markup=search_back_kb(context="mip"),
        )


@mip_search_router.callback_query(SearchUserResult.filter(F.context == "mip"))
async def show_user_details(
    callback: CallbackQuery, callback_data: SearchUserResult, stp_repo: MainRequestsRepo
):
    """Показать детальную информацию о найденном пользователе"""
    user_id = callback_data.user_id
    return_to = callback_data.return_to
    head_id = callback_data.head_id

    try:
        user = await stp_repo.employee.get_user(user_id=user_id)
        user_head = await stp_repo.employee.get_user(fullname=user.head)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        if not user_head:
            await callback.answer(
                "❌ Не найдена информация о руководителе пользователя", show_alert=True
            )
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
            user_info += SearchService.format_head_group_info(group_stats)

        # Определяем возможность редактирования и параметры клавиатуры
        can_edit = user.role in [1, 2, 3]  # Специалисты, дежурные и руководители
        is_head = user.role == 2  # Руководитель
        head_user_id = user.user_id if is_head else 0

        await callback.message.edit_text(
            user_info,
            reply_markup=user_detail_kb(
                user_id,
                return_to,
                head_id,
                context="mip",
                show_edit_buttons=can_edit,
                is_head=is_head,
                head_user_id=head_user_id,
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка при получении информации о пользователе: {e}")
        await callback.answer("❌ Ошибка при получении данных", show_alert=True)


@mip_search_router.callback_query(HeadGroupMenu.filter())
async def show_head_group(
    callback: CallbackQuery, callback_data: HeadGroupMenu, stp_repo: MainRequestsRepo
):
    """Показать группу руководителя (список его сотрудников) с использованием функциональности head group members"""
    head_id = callback_data.head_id
    page = callback_data.page

    try:
        # Получаем информацию о руководителе по user_id
        head_user = await stp_repo.employee.get_user(user_id=head_id)
        if not head_user:
            await callback.answer("❌ Руководитель не найден", show_alert=True)
            return

        # Получаем всех сотрудников этого руководителя
        group_members = await stp_repo.employee.get_users_by_head(head_user.fullname)

        if not group_members:
            await callback.message.edit_text(
                f"""👥 <b>Группа: {head_user.fullname}</b>

У этого руководителя пока нет подчиненных в системе
            
<i>Если это ошибка, обратись к администратору.</i>""",
                reply_markup=head_group_members_kb_for_search(
                    [], current_page=1, head_id=head_id
                ),
            )
            return

        # Показываем группу с использованием того же стиля, что и в head group members
        total_members = len(group_members)

        message_text = f"""👥 <b>Группа: {head_user.fullname}</b>

Участники группы: <b>{total_members}</b>

<blockquote><b>Обозначения</b>
🔒 - не авторизован в боте
👮 - дежурный
🔨 - root</blockquote>

<i>Нажми на участника для просмотра подробной информации</i>"""

        await callback.message.edit_text(
            message_text,
            reply_markup=head_group_members_kb_for_search(
                group_members, current_page=page, head_id=head_id
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка при получении группы руководителя {head_id}: {e}")
        await callback.answer("❌ Ошибка при получении данных группы", show_alert=True)


@mip_search_router.callback_query(EditUserMenu.filter())
async def start_edit_user(
    callback: CallbackQuery,
    callback_data: EditUserMenu,
    state: FSMContext,
    stp_repo: MainRequestsRepo,
):
    """Начать редактирование данных пользователя"""
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

        # Получаем название текущей роли
        current_role_name = (
            roles[user.role]
            if user.role < len(roles)
            else f"Неизвестная роль ({user.role})"
        )

        await callback.message.edit_text(
            f"""🛡️ <b>Изменение уровня доступа</b>

<b>Сотрудник:</b> <a href='t.me/{user.username}'>{user.fullname}</a>
<b>Текущий уровень доступа:</b> {current_role_name}

Выбери новую уровень для пользователя:

<i>Пользователь получит уведомление об изменении</i>""",
            reply_markup=role_selection_kb(user_id, user.role),
        )


@mip_search_router.message(EditEmployee.waiting_new_fullname)
async def process_edit_fullname(
    message: Message, state: FSMContext, stp_repo: MainRequestsRepo
):
    """Обработка изменения ФИО пользователя"""

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


@mip_search_router.callback_query(SearchUserKPIMenu.filter())
async def search_user_kpi_menu(
    callback: CallbackQuery,
    callback_data: SearchUserKPIMenu,
    stp_repo: MainRequestsRepo,
    kpi_repo: KPIRequestsRepo,
):
    """Полноценное KPI меню для пользователя из поиска"""
    user_id = callback_data.user_id
    action = callback_data.action
    return_to = callback_data.return_to
    head_id = callback_data.head_id

    message_text = ""

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
                        user_id, return_to, head_id, action, context="mip"
                    ),
                )
                return

            if action == "main":
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

            elif action == "calculator":
                csi_calculation = KPICalculator.calculate_csi_needed(
                    user.division, premium.csi, premium.csi_normative
                )
                flr_calculation = KPICalculator.calculate_flr_needed(
                    user.division, premium.flr, premium.flr_normative
                )
                gok_calculation = KPICalculator.calculate_gok_needed(
                    user.division, premium.gok, premium.gok_normative
                )
                target_calculation = KPICalculator.calculate_target_needed(
                    premium.target,
                    premium.target_goal_first,
                    premium.target_goal_second,
                    premium.target_type,
                )

                message_text = f"""🧮 <b>Калькулятор KPI</b>

<b>ФИО:</b> <a href="https://t.me/{user.username}">{user.fullname}</a>
<b>Подразделение:</b> {user.position or "Не указано"} {user.division or "Не указано"}

📊 <b>Оценка клиента</b>
<blockquote>Текущий: {SalaryFormatter.format_value(premium.csi)} ({SalaryFormatter.format_percentage(premium.csi_normative_rate)})
План: {SalaryFormatter.format_value(premium.csi_normative)}

<b>Для премии:</b>
{csi_calculation}</blockquote>

🔧 <b>FLR</b>
<blockquote>Текущий: {SalaryFormatter.format_value(premium.flr)} ({SalaryFormatter.format_percentage(premium.flr_normative_rate)})
План: {SalaryFormatter.format_value(premium.flr_normative)}

<b>Для премии:</b>
{flr_calculation}</blockquote>

⚖️ <b>ГОК</b>
<blockquote>Текущий: {SalaryFormatter.format_value(round(premium.gok))} ({SalaryFormatter.format_percentage(premium.gok_normative_rate)})
План: {SalaryFormatter.format_value(round(premium.gok_normative))}

<b>Для премии:</b>
{gok_calculation}</blockquote>

🎯 <b>Цель</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.target)} ({SalaryFormatter.format_percentage(round((premium.target_goal_first / premium.target * 100) if premium.target_type and "AHT" in premium.target_type and premium.target and premium.target > 0 and premium.target_goal_first else (premium.target / premium.target_goal_first * 100) if premium.target_goal_first and premium.target_goal_first > 0 else 0))} / {SalaryFormatter.format_percentage(round((premium.target_goal_second / premium.target * 100) if premium.target_type and "AHT" in premium.target_type and premium.target and premium.target > 0 and premium.target_goal_second else (premium.target / premium.target_goal_second * 100) if premium.target_goal_second and premium.target_goal_second > 0 else 0))})
План: {SalaryFormatter.format_value(round(premium.target_goal_first))} / {SalaryFormatter.format_value(round(premium.target_goal_second))}

Требуется минимум 100 {"чатов" if user.division == "НЦК" else "звонков"} для получения премии за цель

<b>Для премии:</b>
{target_calculation}</blockquote>

<i>Данные от: {premium.updated_at.strftime("%d.%m.%y %H:%M") if premium.updated_at else "—"}</i>"""

            elif action == "salary":
                user_premium = await kpi_repo.spec_premium.get_premium(
                    fullname=user.fullname
                )

                salary_result = await SalaryCalculator.calculate_salary(
                    user=user, premium_data=user_premium
                )

                message_text = SalaryFormatter.format_salary_message(
                    salary_result, user_premium
                )
        except Exception as e:
            logger.error(f"Ошибка при получении KPI для {user.fullname}: {e}")

            message_text = f"""📊 <b>KPI: {user.fullname}</b>

❌ <b>Ошибка загрузки данных</b>

Произошла ошибка при получении показателей эффективности.

<i>Попробуй позже или обратись к администратору для проверки данных</i>"""

        await callback.message.edit_text(
            message_text,
            reply_markup=search_user_kpi_kb(
                user_id, return_to, head_id, action, context="mip"
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка при получении KPI пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка при получении KPI", show_alert=True)


@mip_search_router.callback_query(SearchMemberKPIMenu.filter())
async def search_member_kpi_menu(
    callback: CallbackQuery,
    callback_data: SearchMemberKPIMenu,
    user: Employee,
    stp_repo: MainRequestsRepo,
    kpi_repo: KPIRequestsRepo,
):
    """Полноценное KPI меню для участника группы из поиска"""
    member_id = callback_data.member_id
    head_id = callback_data.head_id
    action = callback_data.action
    page = callback_data.page

    message_text = ""

    try:
        member = await stp_repo.employee.get_user(main_id=member_id)

        if not member:
            await callback.answer("❌ Участник не найден", show_alert=True)
            return

        # Получаем KPI данные участника
        try:
            premium = await kpi_repo.spec_premium.get_premium(fullname=member.fullname)

            if premium is None:
                message_text = f"""📊 <b>KPI: {member.fullname}</b>

❌ <b>Данные KPI не найдены</b>

Показатели эффективности для этого сотрудника отсутствуют в системе или не загружены.

<i>Обратись к администратору для проверки данных</i>"""

                await callback.message.edit_text(
                    message_text,
                    reply_markup=search_member_kpi_kb(member_id, head_id, page, action),
                )
                return

            if action == "main":
                message_text = f"""🌟 <b>Показатели</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or ""}

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

{"📈 Всего чатов: " + SalaryFormatter.format_value(premium.contacts_count) if member.division == "НЦК" else "📈 Всего звонков: " + SalaryFormatter.format_value(premium.contacts_count)}
{"⏰ Задержка: " + SalaryFormatter.format_value(premium.delay, " сек") if member.division != "НЦК" else ""}

<i>Выгружено: {premium.updated_at.strftime("%d.%m.%y %H:%M") if premium.updated_at else "—"}</i>"""

            elif action == "calculator":
                csi_calculation = KPICalculator.calculate_csi_needed(
                    member.division, premium.csi, premium.csi_normative
                )
                flr_calculation = KPICalculator.calculate_flr_needed(
                    member.division, premium.flr, premium.flr_normative
                )
                gok_calculation = KPICalculator.calculate_gok_needed(
                    member.division, premium.gok, premium.gok_normative
                )
                target_calculation = KPICalculator.calculate_target_needed(
                    premium.target,
                    premium.target_goal_first,
                    premium.target_goal_second,
                    premium.target_type,
                )

                message_text = f"""🧮 <b>Калькулятор KPI</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or ""}

📊 <b>Оценка клиента</b>
<blockquote>Текущий: {SalaryFormatter.format_value(premium.csi)} ({SalaryFormatter.format_percentage(premium.csi_normative_rate)})
План: {SalaryFormatter.format_value(premium.csi_normative)}

<b>Для премии:</b>
{csi_calculation}</blockquote>

🔧 <b>FLR</b>
<blockquote>Текущий: {SalaryFormatter.format_value(premium.flr)} ({SalaryFormatter.format_percentage(premium.flr_normative_rate)})
План: {SalaryFormatter.format_value(premium.flr_normative)}

<b>Для премии:</b>
{flr_calculation}</blockquote>

⚖️ <b>ГОК</b>
<blockquote>Текущий: {SalaryFormatter.format_value(round(premium.gok))} ({SalaryFormatter.format_percentage(premium.gok_normative_rate)})
План: {SalaryFormatter.format_value(round(premium.gok_normative))}

<b>Для премии:</b>
{gok_calculation}</blockquote>

🎯 <b>Цель</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.target)} ({SalaryFormatter.format_percentage(round((premium.target_goal_first / premium.target * 100) if premium.target_type and "AHT" in premium.target_type and premium.target and premium.target > 0 and premium.target_goal_first else (premium.target / premium.target_goal_first * 100) if premium.target_goal_first and premium.target_goal_first > 0 else 0))} / {SalaryFormatter.format_percentage(round((premium.target_goal_second / premium.target * 100) if premium.target_type and "AHT" in premium.target_type and premium.target and premium.target > 0 and premium.target_goal_second else (premium.target / premium.target_goal_second * 100) if premium.target_goal_second and premium.target_goal_second > 0 else 0))})
План: {SalaryFormatter.format_value(round(premium.target_goal_first))} / {SalaryFormatter.format_value(round(premium.target_goal_second))}

Требуется минимум 100 {"чатов" if member.division == "НЦК" else "звонков"} для получения премии за цель

<b>Для премии:</b>
{target_calculation}</blockquote>

<i>Данные от: {premium.updated_at.strftime("%d.%m.%y %H:%M") if premium.updated_at else "—"}</i>"""

            elif action == "salary":
                user_premium = await kpi_repo.spec_premium.get_premium(
                    fullname=user.fullname
                )

                salary_result = await SalaryCalculator.calculate_salary(
                    user=user, premium_data=user_premium
                )

                message_text = SalaryFormatter.format_salary_message(
                    salary_result, user_premium
                )

        except Exception as e:
            logger.error(f"Ошибка при получении KPI для {member.fullname}: {e}")

            message_text = f"""📊 <b>KPI: {member.fullname}</b>

❌ <b>Ошибка загрузки данных</b>

Произошла ошибка при получении показателей эффективности.

<i>Попробуй позже или обратись к администратору для проверки данных</i>"""

        await callback.message.edit_text(
            message_text,
            reply_markup=search_member_kpi_kb(member_id, head_id, page, action),
        )

    except Exception as e:
        logger.error(f"Ошибка при получении KPI участника {member_id}: {e}")
        await callback.answer("❌ Ошибка при получении KPI", show_alert=True)


@mip_search_router.callback_query(ViewUserSchedule.filter(F.context == "mip"))
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
                    context="mip",
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
                    context="mip",
                ),
            )

    except Exception as e:
        logger.error(f"Ошибка при получении расписания пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка при получении расписания", show_alert=True)


@mip_search_router.callback_query(ScheduleNavigation.filter(F.context == "mip"))
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
                    context="mip",
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
                    context="mip",
                ),
            )

    except Exception as e:
        logger.error(f"Ошибка при навигации по расписанию пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка при получении расписания", show_alert=True)


@mip_search_router.callback_query(SelectUserRole.filter())
async def process_role_change(
    callback: CallbackQuery, callback_data: SelectUserRole, stp_repo: MainRequestsRepo
):
    """Обработка изменения роли пользователя"""
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
            roles[user.role]
            if user.role < len(roles)
            else f"Неизвестный уровень ({user.role})"
        )
        new_role_name = (
            roles[new_role]
            if new_role < len(roles)
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
        # Создаем новый callback_data для возврата к пользователю
        user_callback_data = SearchUserResult(user_id=user_id)
        await show_user_details(callback, user_callback_data, stp_repo)

    except Exception as e:
        logger.error(f"Ошибка при изменении роли пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка при сохранении роли", show_alert=True)


# Обработчики для search-специфичных callback data (для интеграции с head group members)


@mip_search_router.callback_query(HeadGroupMembersMenuForSearch.filter())
async def group_members_pagination_cb_search(
    callback: CallbackQuery,
    callback_data: HeadGroupMembersMenuForSearch,
    stp_repo: MainRequestsRepo,
):
    """Обработчик пагинации списка участников группы из поиска"""
    head_id = callback_data.head_id
    page = callback_data.page

    try:
        # Получаем информацию о руководителе
        head_user = await stp_repo.employee.get_user(user_id=head_id)
        if not head_user:
            await callback.answer("❌ Руководитель не найден", show_alert=True)
            return

        # Получаем всех сотрудников этого руководителя
        group_members = await stp_repo.employee.get_users_by_head(head_user.fullname)

        if not group_members:
            await callback.answer("❌ Участники не найдены", show_alert=True)
            return

        total_members = len(group_members)

        message_text = f"""👥 <b>Группа: {head_user.fullname}</b>

Участники группы: <b>{total_members}</b>

<blockquote><b>Обозначения</b>
🔒 - не авторизован в боте
👮 - дежурный
🔨 - root</blockquote>

<i>Нажми на участника для просмотра подробной информации</i>"""

        await callback.message.edit_text(
            message_text,
            reply_markup=head_group_members_kb_for_search(
                group_members, current_page=page, head_id=head_id
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка при пагинации группы руководителя {head_id}: {e}")
        await callback.answer("❌ Ошибка при получении данных", show_alert=True)


@mip_search_router.callback_query(HeadMemberDetailMenuForSearch.filter())
async def member_detail_cb_search(
    callback: CallbackQuery,
    callback_data: HeadMemberDetailMenuForSearch,
    stp_repo: MainRequestsRepo,
):
    """Обработчик детального просмотра участника группы из поиска"""
    member_id = callback_data.member_id
    head_id = callback_data.head_id
    page = callback_data.page

    try:
        member = await stp_repo.employee.get_user(main_id=member_id)

        if not member:
            await callback.answer("❌ Участник не найден", show_alert=True)
            return

        # Формируем информацию об участнике
        message_text = f"""👤 <b>Информация об участнике</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or ""}
<b>Email:</b> {member.email or "Не указано"}

🛡️ <b>Уровень доступа:</b> <code>{roles.get(member.role, "Неизвестно")}</code>"""

        # Добавляем статус только для неавторизованных пользователей
        if not member.user_id:
            message_text += "\n<b>Статус:</b> 🔒 Не авторизован в боте"

        message_text += "\n\n<i>Выбери действие:</i>"

        await callback.message.edit_text(
            message_text,
            reply_markup=head_member_detail_kb_for_search(
                member_id, head_id, page, member.role
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка при просмотре участника {member_id}: {e}")
        await callback.answer(
            "❌ Ошибка при получении данных участника", show_alert=True
        )


@mip_search_router.callback_query(HeadMemberActionMenuForSearch.filter())
async def member_action_cb_search(
    callback: CallbackQuery,
    callback_data: HeadMemberActionMenuForSearch,
    stp_repo: MainRequestsRepo,
):
    """Обработчик действий с участником (расписание/KPI/игра) из поиска"""
    member_id = callback_data.member_id
    head_id = callback_data.head_id
    action = callback_data.action
    page = callback_data.page

    try:
        member = await stp_repo.employee.get_user(main_id=member_id)

        if not member:
            await callback.answer("❌ Участник не найден", show_alert=True)
            return

        if action == "schedule":
            # Вызываем обработчик просмотра расписания
            schedule_callback_data = SearchMemberScheduleMenu(
                member_id=member.id, head_id=head_id, month_idx=0, page=page
            )
            await view_search_member_schedule(
                callback, schedule_callback_data, stp_repo
            )
            return

        elif action == "game_profile":
            # Проверяем, что у участника есть user_id (авторизован в боте)
            if not member.user_id:
                await callback.message.edit_text(
                    f"""🏮 <b>Игровой профиль</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>

❌ <b>Пользователь не авторизован в боте</b>

<i>Игровой профиль доступен только для авторизованных пользователей</i>""",
                    reply_markup=head_member_detail_kb_for_search(
                        member_id, head_id, page, member.role
                    ),
                )
                return

            user_balance = await stp_repo.transaction.get_user_balance(
                user_id=member.user_id
            )
            achievements_sum = await stp_repo.transaction.get_user_achievements_sum(
                user_id=member.user_id
            )
            purchases_sum = await stp_repo.purchase.get_user_purchases_sum(
                user_id=member.user_id
            )
            level_info_text = LevelingSystem.get_level_info_text(
                achievements_sum, user_balance
            )

            # Формируем сообщение с игровым профилем
            message_text = f"""🏮 <b>Игровой профиль</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or ""}

{level_info_text}

<blockquote expandable><b>✨ Баланс</b>
Всего заработано: {achievements_sum} баллов
Всего потрачено: {purchases_sum} баллов</blockquote>"""

            await callback.message.edit_text(
                message_text,
                reply_markup=head_member_detail_kb_for_search(
                    member_id, head_id, page, member.role
                ),
            )
            return

        else:
            await callback.answer("❌ Неизвестное действие", show_alert=True)
            return

    except Exception as e:
        logger.error(
            f"Ошибка при выполнении действия {action} для участника {member_id}: {e}"
        )
        await callback.answer("❌ Ошибка при выполнении действия", show_alert=True)


@mip_search_router.callback_query(HeadMemberRoleChangeForSearch.filter())
async def change_member_role_search(
    callback: CallbackQuery,
    callback_data: HeadMemberRoleChangeForSearch,
    stp_repo: MainRequestsRepo,
):
    """Обработчик смены роли участника группы из поиска"""
    member_id = callback_data.member_id
    head_id = callback_data.head_id
    page = callback_data.page

    try:
        member = await stp_repo.employee.get_user(main_id=member_id)

        if not member:
            await callback.answer("❌ Участник не найден", show_alert=True)
            return

        # Проверяем, что роль может быть изменена
        if member.role not in [1, 3]:
            await callback.answer(
                "❌ Уровень доступа этого пользователя нельзя изменить", show_alert=True
            )
            return

        # Определяем новый уровень доступа
        new_role = 3 if member.role == 1 else 1
        old_role_name = "Специалист" if member.role == 1 else "Дежурный"
        new_role_name = "Дежурный" if new_role == 3 else "Специалист"

        # Обновляем уровень в базе данных
        await stp_repo.employee.update_user(user_id=member.user_id, role=new_role)

        # Отправляем уведомление пользователю о смене роли (только если он авторизован)
        if member.user_id:
            try:
                await callback.bot.send_message(
                    chat_id=member.user_id,
                    text=f"""<b>🔔 Изменение роли</b>

Уровень был изменен: {old_role_name} → {new_role_name}

<i>Изменения могут повлиять на доступные функции бота</i>""",
                )
                await callback.answer(
                    "Отправили специалисту уведомление об изменении роли"
                )
            except Exception as e:
                await callback.answer("Не удалось отправить уведомление специалисту :(")
                logger.error(
                    f"Не удалось отправить уведомление пользователю {member.user_id}: {e}"
                )

        logger.info(
            f"[МИП] - [Изменение роли] {callback.from_user.username} ({callback.from_user.id}) изменил роль участника {member_id}: {old_role_name} → {new_role_name}"
        )

        # Возвращаемся к детальной информации участника
        member_detail_callback_data = HeadMemberDetailMenuForSearch(
            member_id=member_id, head_id=head_id, page=page
        )
        await member_detail_cb_search(callback, member_detail_callback_data, stp_repo)

    except Exception as e:
        logger.error(f"Ошибка при изменении роли участника {member_id}: {e}")
        await callback.answer("❌ Ошибка при изменении роли", show_alert=True)


@mip_search_router.callback_query(SearchMemberScheduleMenu.filter())
async def view_search_member_schedule(
    callback: CallbackQuery,
    callback_data: SearchMemberScheduleMenu,
    stp_repo: MainRequestsRepo,
):
    """Обработчик просмотра расписания участника группы из поиска"""
    member_id = callback_data.member_id
    head_id = callback_data.head_id
    requested_month_idx = callback_data.month_idx
    page = callback_data.page

    try:
        member = await stp_repo.employee.get_user(main_id=member_id)

        if not member:
            await callback.answer("❌ Участник не найден", show_alert=True)
            return

        # Определяем месяц для отображения
        if requested_month_idx > 0:
            current_month = get_month_name_by_index(requested_month_idx)
        else:
            current_month = schedule_service.get_current_month()

        try:
            # Получаем расписание участника (компактный формат) с дежурствами
            schedule_response = await schedule_service.get_user_schedule_response(
                user=member, month=current_month, compact=True, stp_repo=stp_repo
            )

            await callback.message.edit_text(
                f"""📅 <b>График участника</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or "Не указано"}

<blockquote>{schedule_response}</blockquote>""",
                reply_markup=search_member_schedule_kb(
                    member_id=member_id,
                    head_id=head_id,
                    current_month=current_month,
                    page=page,
                    is_detailed=False,
                ),
            )

        except Exception as schedule_error:
            # Если не удалось получить расписание, показываем ошибку
            error_message = "❌ График для данного сотрудника не найдено"
            if "не найден" in str(schedule_error).lower():
                error_message = f"❌ Сотрудник {member.fullname} не найден в графике"
            elif "файл" in str(schedule_error).lower():
                error_message = "❌ Файл графика недоступен"

            await callback.message.edit_text(
                f"""📅 <b>График участника</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or "Не указано"}

{error_message}

<i>Возможно, сотрудник не включен в текущий график или файл недоступен.</i>""",
                reply_markup=search_member_schedule_kb(
                    member_id=member_id,
                    head_id=head_id,
                    current_month=current_month,
                    page=page,
                    is_detailed=False,
                ),
            )

    except Exception as e:
        logger.error(f"Ошибка при получении расписания участника {member_id}: {e}")
        await callback.answer("❌ Ошибка при получении расписания", show_alert=True)


@mip_search_router.callback_query(SearchMemberScheduleNavigation.filter())
async def navigate_search_member_schedule(
    callback: CallbackQuery,
    callback_data: SearchMemberScheduleNavigation,
    stp_repo: MainRequestsRepo,
):
    """Навигация по расписанию участника группы из поиска"""
    member_id = callback_data.member_id
    head_id = callback_data.head_id
    action = callback_data.action
    month_idx = callback_data.month_idx
    page = callback_data.page

    try:
        member = await stp_repo.employee.get_user(main_id=member_id)

        if not member:
            await callback.answer("❌ Участник не найден", show_alert=True)
            return

        # Определяем компактность вывода
        compact = action not in ["detailed"]

        # Преобразуем индекс месяца в название
        month_to_display = get_month_name_by_index(month_idx)

        try:
            # Получаем график участника с дежурствами
            schedule_response = await schedule_service.get_user_schedule_response(
                user=member, month=month_to_display, compact=compact, stp_repo=stp_repo
            )

            await callback.message.edit_text(
                f"""📅 <b>График участника</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or "Не указано"}

<blockquote>{schedule_response}</blockquote>""",
                reply_markup=search_member_schedule_kb(
                    member_id=member_id,
                    head_id=head_id,
                    current_month=month_to_display,
                    page=page,
                    is_detailed=not compact,
                ),
            )

        except Exception as schedule_error:
            # Если не удалось получить расписание, показываем ошибку
            error_message = "❌ График для данного сотрудника не найдено"
            if "не найден" in str(schedule_error).lower():
                error_message = f"❌ Сотрудник {member.fullname} не найден в графике"
            elif "файл" in str(schedule_error).lower():
                error_message = "❌ Файл графика недоступен"

            await callback.message.edit_text(
                f"""📅 <b>График участника</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or "Не указано"}

{error_message}

<i>Возможно, сотрудник не включен в текущий график или файл недоступен.</i>""",
                reply_markup=search_member_schedule_kb(
                    member_id=member_id,
                    head_id=head_id,
                    current_month=month_to_display,
                    page=page,
                    is_detailed=not compact,
                ),
            )

    except Exception as e:
        logger.error(f"Ошибка при навигации по расписанию участника {member_id}: {e}")
        await callback.answer("❌ Ошибка при получении расписания", show_alert=True)

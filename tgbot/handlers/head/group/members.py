import datetime
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from infrastructure.api.production_calendar import production_calendar
from infrastructure.database.models import Employee
from infrastructure.database.repo.KPI.requests import KPIRequestsRepo
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import HeadFilter
from tgbot.handlers.group.whois import get_role_info
from tgbot.handlers.user.schedule.main import schedule_service
from tgbot.keyboards.head.group.game_profile import (
    HeadMemberGameHistoryMenu,
    HeadMemberGameProfileMenu,
    HeadMemberTransactionDetailMenu,
    head_member_game_history_kb,
    head_member_game_profile_kb,
    head_member_transaction_detail_kb,
)
from tgbot.keyboards.head.group.main import GroupManagementMenu
from tgbot.keyboards.head.group.members import (
    HeadGroupMembersMenu,
    HeadMemberActionMenu,
    HeadMemberDetailMenu,
    HeadMemberKPIMenu,
    HeadMemberRoleChange,
    HeadMemberScheduleMenu,
    HeadMemberScheduleNavigation,
    get_month_name_by_index,
    head_group_members_kb,
    head_member_detail_kb,
    head_member_schedule_kb,
)
from tgbot.keyboards.head.group.members_kpi import head_member_kpi_kb
from tgbot.misc.dicts import russian_months
from tgbot.services.schedule import ScheduleParser

head_group_members_router = Router()
head_group_members_router.message.filter(F.chat.type == "private", HeadFilter())
head_group_members_router.callback_query.filter(
    F.message.chat.type == "private", HeadFilter()
)

logger = logging.getLogger(__name__)


@head_group_members_router.callback_query(
    GroupManagementMenu.filter(F.menu == "members")
)
async def group_mgmt_members_cb(callback: CallbackQuery, stp_repo: MainRequestsRepo):
    """Обработчик состава группы"""
    # Получаем информацию о текущем пользователе (руководителе)
    current_user = await stp_repo.employee.get_user(user_id=callback.from_user.id)

    if not current_user:
        await callback.message.edit_text(
            """❌ <b>Ошибка</b>
            
Не удалось найти вашу информацию в базе данных."""
        )
        return

    # Получаем всех сотрудников этого руководителя
    group_members = await stp_repo.employee.get_users_by_head(current_user.fullname)

    if not group_members:
        await callback.message.edit_text(
            """👥 <b>Состав группы</b>

У тебя пока нет подчиненных в системе
            
<i>Если это ошибка, обратись к администратору.</i>""",
            reply_markup=head_group_members_kb([], current_page=1),
        )
        return

    # Показываем первую страницу по умолчанию
    total_members = len(group_members)

    message_text = f"""👥 <b>Состав группы</b>

Участники твоей группы: <b>{total_members}</b>

<blockquote><b>Обозначения</b>
🔒 - не авторизован в боте
👮 - дежурный
🔨 - root</blockquote>

<i>Нажми на участника для просмотра подробной информации</i>"""

    await callback.message.edit_text(
        message_text,
        reply_markup=head_group_members_kb(group_members, current_page=1),
    )


@head_group_members_router.callback_query(HeadGroupMembersMenu.filter())
async def group_members_pagination_cb(
    callback: CallbackQuery,
    callback_data: HeadGroupMembersMenu,
    stp_repo: MainRequestsRepo,
):
    """Обработчик пагинации списка участников группы"""
    # Получаем информацию о текущем пользователе (руководителе)
    current_user = await stp_repo.employee.get_user(user_id=callback.from_user.id)

    if not current_user:
        await callback.answer("❌ Ошибка получения данных", show_alert=True)
        return

    # Получаем всех сотрудников этого руководителя
    group_members = await stp_repo.employee.get_users_by_head(current_user.fullname)

    if not group_members:
        await callback.answer("❌ Участники не найдены", show_alert=True)
        return

    total_members = len(group_members)
    page = callback_data.page

    message_text = f"""👥 <b>Состав группы</b>

Участники вашей группы: <b>{total_members}</b>

<blockquote><b>Обозначения</b>
🔒 - не авторизован в боте
👮 - дежурный
🔨 - root</blockquote>

<i>Нажми на участника для просмотра подробной информации</i>"""

    await callback.message.edit_text(
        message_text,
        reply_markup=head_group_members_kb(group_members, current_page=page),
    )


@head_group_members_router.callback_query(HeadMemberDetailMenu.filter())
async def member_detail_cb(
    callback: CallbackQuery,
    callback_data: HeadMemberDetailMenu,
    stp_repo: MainRequestsRepo,
):
    """Обработчик детального просмотра участника группы"""
    # Поиск участника по ID
    all_users = await stp_repo.employee.get_users()
    member = None
    for user in all_users:
        if user.id == callback_data.member_id:
            member = user
            break

    if not member:
        await callback.answer("❌ Участник не найден", show_alert=True)
        return

    # Формируем информацию об участнике
    message_text = f"""👤 <b>Информация об участнике</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or ""}
<b>Email:</b> {member.email or "Не указано"}

🛡️ <b>Уровень доступа:</b> <code>{get_role_info(member.role)["text"]}</code>"""

    # Добавляем статус только для неавторизованных пользователей
    if not member.user_id:
        message_text += "\n<b>Статус:</b> 🔒 Не авторизован в боте"

    message_text += "\n\n<i>Выбери действие:</i>"

    await callback.message.edit_text(
        message_text,
        reply_markup=head_member_detail_kb(member.id, callback_data.page, member.role),
    )


@head_group_members_router.callback_query(HeadMemberActionMenu.filter())
async def member_action_cb(
    callback: CallbackQuery,
    callback_data: HeadMemberActionMenu,
    stp_repo: MainRequestsRepo,
    kpi_repo: KPIRequestsRepo,
):
    """Обработчик действий с участником (расписание/KPI)"""
    # Поиск участника по ID
    all_users = await stp_repo.employee.get_users()
    member = None
    for user in all_users:
        if user.id == callback_data.member_id:
            member = user
            break

    if not member:
        await callback.answer("❌ Участник не найден", show_alert=True)
        return

    if callback_data.action == "schedule":
        # Вызываем обработчик просмотра расписания
        schedule_callback_data = HeadMemberScheduleMenu(
            member_id=member.id, month_idx=0, page=callback_data.page
        )
        await view_member_schedule(callback, schedule_callback_data, stp_repo)
        return

    elif callback_data.action == "game_profile":
        # Вызываем обработчик просмотра игрового профиля
        game_profile_callback_data = HeadMemberGameProfileMenu(
            member_id=member.id, page=callback_data.page
        )
        await view_member_game_profile(callback, game_profile_callback_data, stp_repo)
        return

    else:
        await callback.answer("❌ Неизвестное действие", show_alert=True)
        return


@head_group_members_router.callback_query(HeadMemberScheduleMenu.filter())
async def view_member_schedule(
    callback: CallbackQuery,
    callback_data: HeadMemberScheduleMenu,
    stp_repo: MainRequestsRepo,
):
    """Обработчик просмотра расписания участника группы"""
    member_id = callback_data.member_id
    requested_month_idx = callback_data.month_idx
    page = callback_data.page

    try:
        # Поиск участника по ID
        all_users = await stp_repo.employee.get_users()
        member = None
        for user in all_users:
            if user.id == member_id:
                member = user
                break

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
                reply_markup=head_member_schedule_kb(
                    member_id=member_id,
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
                reply_markup=head_member_schedule_kb(
                    member_id=member_id,
                    current_month=current_month,
                    page=page,
                    is_detailed=False,
                ),
            )

    except Exception as e:
        logger.error(f"Ошибка при получении расписания участника {member_id}: {e}")
        await callback.answer("❌ Ошибка при получении расписания", show_alert=True)


@head_group_members_router.callback_query(HeadMemberScheduleNavigation.filter())
async def navigate_member_schedule(
    callback: CallbackQuery,
    callback_data: HeadMemberScheduleNavigation,
    stp_repo: MainRequestsRepo,
):
    """Навигация по расписанию участника группы"""
    member_id = callback_data.member_id
    action = callback_data.action
    month_idx = callback_data.month_idx
    page = callback_data.page

    try:
        # Поиск участника по ID
        all_users = await stp_repo.employee.get_users()
        member = None
        for user in all_users:
            if user.id == member_id:
                member = user
                break

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
                reply_markup=head_member_schedule_kb(
                    member_id=member_id,
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
                reply_markup=head_member_schedule_kb(
                    member_id=member_id,
                    current_month=month_to_display,
                    page=page,
                    is_detailed=not compact,
                ),
            )

    except Exception as e:
        logger.error(f"Ошибка при навигации по расписанию участника {member_id}: {e}")
        await callback.answer("❌ Ошибка при получении расписания", show_alert=True)


@head_group_members_router.callback_query(HeadMemberKPIMenu.filter())
async def view_member_kpi(
    callback: CallbackQuery,
    callback_data: HeadMemberKPIMenu,
    stp_repo: MainRequestsRepo,
    kpi_repo: KPIRequestsRepo,
):
    """Обработчик KPI меню участника группы"""
    member_id = callback_data.member_id
    action = callback_data.action
    page = callback_data.page

    try:
        # Поиск участника по ID
        all_users = await stp_repo.employee.get_users()
        member = None
        for user in all_users:
            if user.id == member_id:
                member = user
                break

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
                    reply_markup=head_member_kpi_kb(member_id, page, action),
                )
                return

            def format_value(value, suffix=""):
                return f"{value}{suffix}" if value is not None else "—"

            def format_percentage(value):
                return f"{value}%" if value is not None else "—"

            if action == "main":
                message_text = f"""🌟 <b>Показатели</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or ""}

📊 <b>Оценка клиента - {format_percentage(premium.csi_premium)}</b>
<blockquote>Факт: {format_value(premium.csi)}
План: {format_value(premium.csi_normative)}</blockquote>

🎯 <b>Отклик</b>
<blockquote>Факт: {format_value(premium.csi_response)}
План: {format_value(round(premium.csi_response_normative)) if premium.csi_response_normative else "—"}</blockquote>

🔧 <b>FLR - {format_percentage(premium.flr_premium)}</b>
<blockquote>Факт: {format_value(premium.flr)}
План: {format_value(premium.flr_normative)}</blockquote>

⚖️ <b>ГОК - {format_percentage(premium.gok_premium)}</b>
<blockquote>Факт: {format_value(premium.gok)}
План: {format_value(premium.gok_normative)}</blockquote>

🎯 <b>Цель - {format_percentage(premium.target_premium)}</b>
<blockquote>Тип: {premium.target_type or "—"}
Факт: {format_value(premium.target)}
План: {format_value(round(premium.target_goal_first)) if premium.target_goal_first else "—"} / {format_value(round(premium.target_goal_second)) if premium.target_goal_second else "—"}</blockquote>

💼 <b>Дополнительно</b>
<blockquote>Дисциплина: {format_percentage(premium.discipline_premium)}
Тестирование: {format_percentage(premium.tests_premium)}
Благодарности: {format_percentage(premium.thanks_premium)}
Наставничество: {format_percentage(premium.tutors_premium)}
Ручная правка: {format_percentage(premium.head_adjust_premium)}</blockquote>

💰 <b>Итого:</b>
<b>Общая премия: {format_percentage(premium.total_premium)}</b>

{"📈 Всего чатов: " + format_value(premium.contacts_count) if member.division == "НЦК" else "📈 Всего звонков: " + format_value(premium.contacts_count)}
{"⏰ Задержка: " + format_value(premium.delay, " сек") if member.division != "НЦК" else ""}

<i>Выгружено: {premium.updated_at.strftime("%d.%m.%y %H:%M") if premium.updated_at else "—"}</i>"""

            elif action == "calculator":
                # Реализация калькулятора KPI аналогично пользовательскому
                def calculate_csi_needed(division: str, current_csi, normative):
                    if normative == 0 or normative is None:
                        return "—"

                    current_csi = current_csi or 0

                    results = []

                    if division == "НЦК":
                        thresholds = [
                            (101, 20, "≥ 101%"),
                            (100.5, 15, "≥ 100,5%"),
                            (100, 10, "≥ 100%"),
                            (98, 5, "≥ 98%"),
                            (0, 0, "&lt; 98%"),
                        ]
                    elif division == "НТП1":
                        thresholds = [
                            (101, 20, "≥ 101%"),
                            (100.5, 15, "≥ 100,5%"),
                            (100, 10, "≥ 100%"),
                            (98, 5, "≥ 98%"),
                            (0, 0, "&lt; 98%"),
                        ]
                    else:
                        thresholds = [
                            (100.8, 20, "≥ 100.8%"),
                            (100.4, 15, "≥ 100.4%"),
                            (100, 10, "≥ 100%"),
                            (98, 5, "≥ 98%"),
                            (0, 0, "&lt; 98%"),
                        ]

                    for threshold, premium_percent, description in thresholds:
                        needed_csi = (threshold / 100) * normative

                        if current_csi >= needed_csi:
                            results.append(f"{premium_percent}%: ✅ ({description})")
                        else:
                            difference = needed_csi - current_csi
                            results.append(
                                f"{premium_percent}%: {needed_csi:.3f} [+{difference:.3f}] ({description})"
                            )

                    return "\n".join(results)

                def calculate_flr_needed(division: str, current_flr, normative):
                    if normative == 0 or normative is None:
                        return "—"

                    current_flr = current_flr or 0

                    results = []

                    if division == "НЦК":
                        thresholds = [
                            (103, 30, "≥ 103%"),
                            (102, 25, "≥ 102%"),
                            (101, 21, "≥ 101%"),
                            (100, 18, "≥ 100%"),
                            (95, 13, "≥ 95%"),
                            (0, 8, "&lt; 95%"),
                        ]
                    elif division == "НТП1":
                        thresholds = [
                            (109, 30, "≥ 109%"),
                            (106, 25, "≥ 106%"),
                            (103, 21, "≥ 103%"),
                            (100, 18, "≥ 100%"),
                            (90, 13, "≥ 90%"),
                            (0, 8, "&lt; 90%"),
                        ]
                    else:
                        thresholds = [
                            (107, 30, "≥ 107%"),
                            (104, 25, "≥ 104%"),
                            (102, 21, "≥ 102%"),
                            (100, 18, "≥ 100%"),
                            (97, 13, "≥ 97%"),
                            (0, 8, "&lt; 97%"),
                        ]

                    for threshold, premium_percent, description in thresholds:
                        needed_flr = (threshold / 100) * normative

                        if current_flr >= needed_flr:
                            results.append(f"{premium_percent}%: ✅ ({description})")
                        else:
                            difference = needed_flr - current_flr
                            results.append(
                                f"{premium_percent}%: {needed_flr:.2f} [+{difference:.2f}] ({description})"
                            )

                    return "\n".join(results)

                def calculate_gok_needed(division: str, current_gok, normative):
                    if normative == 0 or normative is None:
                        return "—"

                    current_gok = current_gok or 0

                    results = []

                    if division == "НЦК":
                        thresholds = [
                            (100, 17, "≥ 100%"),
                            (95, 15, "≥ 95%"),
                            (90, 12, "≥ 90%"),
                            (85, 9, "≥ 85%"),
                            (80, 5, "≥ 80%"),
                            (0, 0, "&lt; 80%"),
                        ]
                    elif division == "НТП1":
                        thresholds = [
                            (100, 17, "≥ 100%"),
                            (95, 15, "≥ 95%"),
                            (90, 12, "≥ 90%"),
                            (85, 9, "≥ 85%"),
                            (80, 5, "≥ 80%"),
                            (0, 0, "&lt; 80%"),
                        ]
                    else:
                        thresholds = [
                            (100, 17, "≥ 100%"),
                            (95, 15, "≥ 95%"),
                            (90, 12, "≥ 90%"),
                            (84, 9, "≥ 84%"),
                            (70, 5, "≥ 70%"),
                            (0, 0, "&lt; 70%"),
                        ]

                    for threshold, premium_percent, description in thresholds:
                        needed_gok = (threshold / 100) * normative

                        if current_gok >= needed_gok:
                            results.append(f"{premium_percent}%: ✅ ({description})")
                        else:
                            difference = needed_gok - current_gok
                            results.append(
                                f"{premium_percent}%: {needed_gok:.3f} [+{difference:.3f}] ({description})"
                            )

                    return "\n".join(results)

                def calculate_target_needed(
                    current_target,
                    target_goal_first,
                    target_goal_second,
                    target_type=None,
                ):
                    if target_goal_first is None and target_goal_second is None:
                        return "—"

                    current_target = current_target or 0

                    # Determine if this is a sales target (higher is better) or AHT target (lower is better)
                    is_sales_target = (
                        target_type and "Продажа оборудования" in target_type
                    )
                    is_aht_target = target_type and "AHT" in target_type

                    results = []

                    # All divisions have the same target premium thresholds
                    if target_goal_second and target_goal_second > 0:
                        # When there's a second goal, use it as the main normative
                        normative = target_goal_second

                        if is_aht_target:
                            # For AHT, lower is better - calculate percentage as (normative / current * 100)
                            target_rate = (
                                (normative / current_target * 100)
                                if current_target > 0
                                else 0
                            )
                        elif is_sales_target:
                            # For sales, higher is better - calculate percentage as (current / normative * 100)
                            target_rate = (
                                (current_target / normative * 100)
                                if normative > 0
                                else 0
                            )
                        else:
                            # Default behavior (higher is better) - calculate percentage as (current / normative * 100)
                            target_rate = (
                                (current_target / normative * 100)
                                if normative > 0
                                else 0
                            )

                        if target_rate > 100.01:
                            results.append("28%: ✅ (≥ 100,01% - план 2 и более)")
                        else:
                            if is_aht_target:
                                # For AHT, we need to be lower than the target
                                needed_for_28 = normative / (100.01 / 100)
                                difference = current_target - needed_for_28
                                results.append(
                                    f"28%: {needed_for_28:.2f} [-{difference:.2f}] (≥ 100,01% - план 2 и более)"
                                )
                            else:
                                # For sales, we need to be higher than the target
                                needed_for_28 = (100.01 / 100) * normative
                                difference = needed_for_28 - current_target
                                results.append(
                                    f"28%: {needed_for_28:.2f} [+{difference:.2f}] (≥ 100,01% - план 2 и более)"
                                )

                        if target_rate >= 100.00:
                            results.append(
                                "18%: ✅ (≥ 100,00% - план 1 и менее плана 2)"
                            )
                        else:
                            if is_aht_target:
                                needed_for_18 = normative / (100.00 / 100)
                                difference = current_target - needed_for_18
                                results.append(
                                    f"18%: {needed_for_18:.2f} [-{difference:.2f}] (= 100,00% - план 1 и менее плана 2)"
                                )
                            else:
                                needed_for_18 = (100.00 / 100) * normative
                                difference = needed_for_18 - current_target
                                results.append(
                                    f"18%: {needed_for_18:.2f} [+{difference:.2f}] (= 100,00% - план 1 и менее плана 2)"
                                )

                        if target_rate < 99.99:
                            results.append("0%: — (&lt; 99,99% - менее плана 1)")
                        else:
                            results.append("0%: ✅ (&lt; 99,99% - менее плана 1)")

                    elif target_goal_first and target_goal_first > 0:
                        # When there's only first goal, use it as normative
                        normative = target_goal_first

                        if is_aht_target:
                            # For AHT, lower is better
                            target_rate = (
                                (normative / current_target * 100)
                                if current_target > 0
                                else 0
                            )
                        elif is_sales_target:
                            # For sales, higher is better
                            target_rate = (
                                (current_target / normative * 100)
                                if normative > 0
                                else 0
                            )
                        else:
                            # Default behavior (higher is better)
                            target_rate = (
                                (current_target / normative * 100)
                                if normative > 0
                                else 0
                            )

                        if target_rate > 100.01:
                            results.append("28%: ✅ (≥ 100,01% - план 2 и более)")
                        else:
                            if is_aht_target:
                                needed_for_28 = normative / (100.01 / 100)
                                difference = current_target - needed_for_28
                                results.append(
                                    f"28%: {needed_for_28:.2f} [-{difference:.2f}] (≥ 100,01% - план 2 и более)"
                                )
                            else:
                                needed_for_28 = (100.01 / 100) * normative
                                difference = needed_for_28 - current_target
                                results.append(
                                    f"28%: {needed_for_28:.2f} [+{difference:.2f}] (≥ 100,01% - план 2 и более)"
                                )

                        if target_rate >= 100.00:
                            results.append(
                                "18%: ✅ (≥ 100,00% - план 1 и менее плана 2)"
                            )
                        else:
                            if is_aht_target:
                                needed_for_18 = normative / (100.00 / 100)
                                difference = current_target - needed_for_18
                                results.append(
                                    f"18%: {needed_for_18:.2f} [-{difference:.2f}] (≥ 100,00% - план 1 и менее плана 2)"
                                )
                            else:
                                needed_for_18 = (100.00 / 100) * normative
                                difference = needed_for_18 - current_target
                                results.append(
                                    f"18%: {needed_for_18:.2f} [+{difference:.2f}] (≥ 100,00% - план 1 и менее плана 2)"
                                )

                        if target_rate < 99.99:
                            results.append("0%: — (&lt; 99,99% - менее плана 1)")
                        else:
                            results.append("0%: ✅ (&lt; 99,99% - менее плана 1)")

                    return "\n".join(results)

                csi_calculation = calculate_csi_needed(
                    member.division, premium.csi, premium.csi_normative
                )
                flr_calculation = calculate_flr_needed(
                    member.division, premium.flr, premium.flr_normative
                )
                gok_calculation = calculate_gok_needed(
                    member.division, premium.gok, premium.gok_normative
                )
                target_calculation = calculate_target_needed(
                    premium.target,
                    premium.target_goal_first,
                    premium.target_goal_second,
                    premium.target_type,
                )

                message_text = f"""🧮 <b>Калькулятор KPI</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or ""}

📊 <b>Оценка клиента</b>
<blockquote>Текущий: {format_value(premium.csi)} ({format_percentage(premium.csi_normative_rate)})
План: {format_value(premium.csi_normative)}

<b>Для премии:</b>
{csi_calculation}</blockquote>

🔧 <b>FLR</b>
<blockquote>Текущий: {format_value(premium.flr)} ({format_percentage(premium.flr_normative_rate)})
План: {format_value(premium.flr_normative)}

<b>Для премии:</b>
{flr_calculation}</blockquote>

⚖️ <b>ГОК</b>
<blockquote>Текущий: {format_value(round(premium.gok))} ({format_percentage(premium.gok_normative_rate)})
План: {format_value(round(premium.gok_normative))}

<b>Для премии:</b>
{gok_calculation}</blockquote>

🎯 <b>Цель</b>
<blockquote>Факт: {format_value(premium.target)} ({format_percentage(round((premium.target_goal_first / premium.target * 100) if premium.target_type and "AHT" in premium.target_type and premium.target and premium.target > 0 and premium.target_goal_first else (premium.target / premium.target_goal_first * 100) if premium.target_goal_first and premium.target_goal_first > 0 else 0))} / {format_percentage(round((premium.target_goal_second / premium.target * 100) if premium.target_type and "AHT" in premium.target_type and premium.target and premium.target > 0 and premium.target_goal_second else (premium.target / premium.target_goal_second * 100) if premium.target_goal_second and premium.target_goal_second > 0 else 0))})
План: {format_value(round(premium.target_goal_first))} / {format_value(round(premium.target_goal_second))}

Требуется минимум 100 {"чатов" if member.division == "НЦК" else "звонков"} для получения премии за цель

<b>Для премии:</b>
{target_calculation}</blockquote>

<i>Данные от: {premium.updated_at.strftime("%d.%m.%y %H:%M") if premium.updated_at else "—"}</i>"""

            elif action == "salary":
                # Реализация расчета зарплаты аналогично пользовательскому
                def format_value(value, suffix=""):
                    return f"{value}{suffix}" if value is not None else "—"

                def format_percentage(value):
                    return f"{value}%" if value is not None else "—"

                pay_rate = 0.0
                match member.division:
                    case "НЦК":
                        match member.position:
                            case "Специалист":
                                pay_rate = 156.7
                            case "Ведущий специалист":
                                pay_rate = 164.2
                            case "Эксперт":
                                pay_rate = 195.9
                    case "НТП1":
                        match member.position:
                            case "Специалист первой линии":
                                pay_rate = 143.6
                    case "НТП2":
                        match member.position:
                            case "Специалист второй линии":
                                pay_rate = 166
                            case "Ведущий специалист второй линии":
                                pay_rate = 181
                            case "Эксперт второй линии":
                                pay_rate = 195.9

                # Get current month working hours from actual schedule
                now = datetime.datetime.now(
                    datetime.timezone(datetime.timedelta(hours=5))
                )
                current_month_name = russian_months[now.month]

                def calculate_night_hours(start_hour, start_min, end_hour, end_min):
                    """Calculate night hours (22:00-06:00) from a work shift"""
                    start_minutes = start_hour * 60 + start_min
                    end_minutes = end_hour * 60 + end_min

                    # Handle overnight shifts
                    if end_minutes < start_minutes:
                        end_minutes += 24 * 60

                    night_start = 22 * 60  # 22:00 in minutes
                    night_end = 6 * 60  # 06:00 in minutes (next day)

                    total_night_minutes = 0

                    # Check for night hours in first day (22:00-24:00)
                    first_day_night_start = night_start
                    first_day_night_end = 24 * 60  # Midnight

                    if (
                        start_minutes < first_day_night_end
                        and end_minutes > first_day_night_start
                    ):
                        overlap_start = max(start_minutes, first_day_night_start)
                        overlap_end = min(end_minutes, first_day_night_end)
                        if overlap_end > overlap_start:
                            total_night_minutes += overlap_end - overlap_start

                    # Check for night hours in second day (00:00-06:00)
                    if end_minutes > 24 * 60:  # Shift continues to next day
                        second_day_start = 24 * 60
                        second_day_end = end_minutes
                        second_day_night_start = 24 * 60  # 00:00 next day
                        second_day_night_end = 24 * 60 + night_end  # 06:00 next day

                        if (
                            second_day_start < second_day_night_end
                            and second_day_end > second_day_night_start
                        ):
                            overlap_start = max(
                                second_day_start, second_day_night_start
                            )
                            overlap_end = min(second_day_end, second_day_night_end)
                            if overlap_end > overlap_start:
                                total_night_minutes += overlap_end - overlap_start

                    return total_night_minutes / 60  # Convert to hours

                # Get actual schedule data with additional shifts detection
                schedule_parser = ScheduleParser()
                try:
                    schedule_data, additional_shifts_data = (
                        schedule_parser.get_user_schedule_with_additional_shifts(
                            member.fullname, current_month_name, member.division
                        )
                    )

                    # Calculate actual working hours from schedule with holiday detection
                    total_working_hours = 0
                    working_days = 0
                    holiday_hours = 0
                    holiday_days_worked = []
                    night_hours = 0
                    night_holiday_hours = 0

                    # Additional shift tracking
                    additional_shift_hours = 0
                    additional_shift_holiday_hours = 0
                    additional_shift_days_worked = []
                    additional_shift_night_hours = 0
                    additional_shift_night_holiday_hours = 0

                    # Process regular schedule
                    for day, schedule_time in schedule_data.items():
                        if schedule_time and schedule_time not in [
                            "Не указано",
                            "В",
                            "О",
                        ]:
                            # Parse time format like "08:00-17:00"
                            import re

                            time_match = re.search(
                                r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})", schedule_time
                            )
                            if time_match:
                                start_hour, start_min, end_hour, end_min = map(
                                    int, time_match.groups()
                                )
                                start_minutes = start_hour * 60 + start_min
                                end_minutes = end_hour * 60 + end_min

                                # Handle overnight shifts
                                if end_minutes < start_minutes:
                                    end_minutes += 24 * 60

                                day_hours = (end_minutes - start_minutes) / 60

                                # Calculate night hours for this shift
                                shift_night_hours = calculate_night_hours(
                                    start_hour, start_min, end_hour, end_min
                                )

                                # For 12-hour shifts, subtract 1 hour for lunch break
                                if day_hours == 12:
                                    day_hours = 11
                                    # Adjust night hours proportionally if lunch break affects them
                                    if shift_night_hours > 0:
                                        shift_night_hours = shift_night_hours * (
                                            11 / 12
                                        )

                                # Check if this day is a holiday
                                try:
                                    work_date = datetime.date(
                                        now.year, now.month, int(day)
                                    )
                                    is_holiday = await production_calendar.is_holiday(
                                        work_date
                                    )
                                    holiday_name = (
                                        await production_calendar.get_holiday_name(
                                            work_date
                                        )
                                    )

                                    if is_holiday and holiday_name:
                                        holiday_hours += day_hours
                                        night_holiday_hours += shift_night_hours
                                        holiday_days_worked.append(
                                            f"{day} - {holiday_name} (+{day_hours:.0f}ч)"
                                        )
                                    else:
                                        night_hours += shift_night_hours
                                except (ValueError, Exception):
                                    # Ignore date parsing errors or API failures
                                    night_hours += shift_night_hours

                                total_working_hours += day_hours
                                working_days += 1

                    # Process additional shifts
                    for day, schedule_time in additional_shifts_data.items():
                        if schedule_time and schedule_time not in [
                            "Не указано",
                            "В",
                            "О",
                        ]:
                            # Parse time format like "08:00-17:00"
                            import re

                            time_match = re.search(
                                r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})", schedule_time
                            )
                            if time_match:
                                start_hour, start_min, end_hour, end_min = map(
                                    int, time_match.groups()
                                )
                                start_minutes = start_hour * 60 + start_min
                                end_minutes = end_hour * 60 + end_min

                                # Handle overnight shifts
                                if end_minutes < start_minutes:
                                    end_minutes += 24 * 60

                                day_hours = (end_minutes - start_minutes) / 60

                                # Calculate night hours for this additional shift
                                shift_night_hours = calculate_night_hours(
                                    start_hour, start_min, end_hour, end_min
                                )

                                # For 12-hour shifts, subtract 1 hour for lunch break
                                if day_hours == 12:
                                    day_hours = 11
                                    # Adjust night hours proportionally if lunch break affects them
                                    if shift_night_hours > 0:
                                        shift_night_hours = shift_night_hours * (
                                            11 / 12
                                        )

                                # Check if this day is a holiday
                                try:
                                    work_date = datetime.date(
                                        now.year, now.month, int(day)
                                    )
                                    is_holiday = await production_calendar.is_holiday(
                                        work_date
                                    )
                                    holiday_name = (
                                        await production_calendar.get_holiday_name(
                                            work_date
                                        )
                                    )

                                    if is_holiday and holiday_name:
                                        additional_shift_holiday_hours += day_hours
                                        additional_shift_night_holiday_hours += (
                                            shift_night_hours
                                        )
                                        additional_shift_days_worked.append(
                                            f"{day} - {holiday_name} (+{day_hours:.0f}ч доп.)"
                                        )
                                    else:
                                        additional_shift_night_hours += (
                                            shift_night_hours
                                        )
                                        additional_shift_days_worked.append(
                                            f"{day} - Доп. смена (+{day_hours:.0f}ч)"
                                        )
                                except (ValueError, Exception):
                                    # Ignore date parsing errors or API failures
                                    additional_shift_night_hours += shift_night_hours
                                    additional_shift_days_worked.append(
                                        f"{day} - Доп. смена (+{day_hours:.0f}ч)"
                                    )

                                additional_shift_hours += day_hours

                except Exception as e:
                    # If schedule calculation fails, show basic info
                    message_text = f"""💰 <b>Расчет зарплаты</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or ""}

❌ <b>Ошибка расчета</b>

Не удалось получить данные расписания для расчета зарплаты.

<i>Ошибка: {str(e)}</i>"""
                else:
                    # Calculate salary components with holiday x2 multiplier, night hours x1.2, and additional shifts
                    # Separate regular and night hours
                    regular_hours = (
                        total_working_hours
                        - holiday_hours
                        - night_hours
                        - night_holiday_hours
                    )
                    regular_additional_shift_hours = (
                        additional_shift_hours
                        - additional_shift_holiday_hours
                        - additional_shift_night_hours
                        - additional_shift_night_holiday_hours
                    )

                    # Base salary calculation
                    base_salary = (
                        (regular_hours * pay_rate)
                        + (holiday_hours * pay_rate * 2)
                        + (night_hours * pay_rate * 1.2)
                        + (night_holiday_hours * pay_rate * 2.4)
                    )

                    # Additional shifts calculation: (pay_rate * 2) + (pay_rate * 0.63) per hour
                    additional_shift_rate = (pay_rate * 2) + (pay_rate * 0.63)
                    additional_shift_holiday_rate = (
                        additional_shift_rate * 2
                    )  # Double for holidays
                    additional_shift_night_rate = (
                        additional_shift_rate * 1.2
                    )  # Night multiplier
                    additional_shift_night_holiday_rate = (
                        additional_shift_rate * 2.4
                    )  # Night + holiday

                    additional_shift_salary = (
                        (regular_additional_shift_hours * additional_shift_rate)
                        + (
                            additional_shift_holiday_hours
                            * additional_shift_holiday_rate
                        )
                        + (additional_shift_night_hours * additional_shift_night_rate)
                        + (
                            additional_shift_night_holiday_hours
                            * additional_shift_night_holiday_rate
                        )
                    )

                    # Calculate individual KPI premium amounts (based only on base salary, not additional shifts)
                    csi_premium_amount = base_salary * (
                        (premium.csi_premium or 0) / 100
                    )
                    flr_premium_amount = base_salary * (
                        (premium.flr_premium or 0) / 100
                    )
                    gok_premium_amount = base_salary * (
                        (premium.gok_premium or 0) / 100
                    )
                    target_premium_amount = base_salary * (
                        (premium.target_premium or 0) / 100
                    )
                    discipline_premium_amount = base_salary * (
                        (premium.discipline_premium or 0) / 100
                    )
                    tests_premium_amount = base_salary * (
                        (premium.tests_premium or 0) / 100
                    )
                    thanks_premium_amount = base_salary * (
                        (premium.thanks_premium or 0) / 100
                    )
                    tutors_premium_amount = base_salary * (
                        (premium.tutors_premium or 0) / 100
                    )
                    head_adjust_premium_amount = base_salary * (
                        (premium.head_adjust_premium or 0) / 100
                    )

                    premium_multiplier = (premium.total_premium or 0) / 100
                    premium_amount = base_salary * premium_multiplier
                    total_salary = (
                        base_salary + premium_amount + additional_shift_salary
                    )

                    message_text = f"""💰 <b>Расчет зарплаты</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or ""}

📅 <b>Период:</b> {current_month_name} {now.year}

⏰ <b>Рабочие часы:</b>
<blockquote>Рабочих дней: {working_days}
Всего часов: {round(total_working_hours)}{
                        f'''

🎉 Праздничные дни (x2): {round(holiday_hours)}ч
{chr(10).join(holiday_days_worked)}'''
                        if holiday_days_worked
                        else ""
                    }{
                        f'''

⭐ Доп. смены: {round(additional_shift_hours)}ч
{chr(10).join(additional_shift_days_worked)}'''
                        if additional_shift_days_worked
                        else ""
                    }</blockquote>

💵 <b>Оклад:</b>
<blockquote>Ставка в час: {format_value(pay_rate, " ₽")}

{
                        chr(10).join(
                            [
                                line
                                for line in [
                                    f"Обычные часы: {round(regular_hours)}ч × {pay_rate} ₽ = {round(regular_hours * pay_rate)} ₽"
                                    if regular_hours > 0
                                    else None,
                                    f"Ночные часы: {round(night_hours)}ч × {round(pay_rate * 1.2, 2)} ₽ = {round(night_hours * pay_rate * 1.2)} ₽"
                                    if night_hours > 0
                                    else None,
                                    f"Праздничные часы: {round(holiday_hours)}ч × {pay_rate * 2} ₽ = {round(holiday_hours * pay_rate * 2)} ₽"
                                    if holiday_hours > 0
                                    else None,
                                    f"Ночные праздничные часы: {round(night_holiday_hours)}ч × {round(pay_rate * 2.4, 2)} ₽ = {round(night_holiday_hours * pay_rate * 2.4)} ₽"
                                    if night_holiday_hours > 0
                                    else None,
                                ]
                                if line is not None
                            ]
                        )
                    }

Сумма оклада: {format_value(round(base_salary), " ₽")}</blockquote>{
                        f'''

⭐ <b>Доп. смены:</b>
<blockquote>{
                            chr(10).join(
                                [
                                    line
                                    for line in [
                                        f"Обычные доп. смены: {round(regular_additional_shift_hours)}ч × {additional_shift_rate:.2f} ₽ = {round(regular_additional_shift_hours * additional_shift_rate)} ₽"
                                        if regular_additional_shift_hours > 0
                                        else None,
                                        f"Ночные доп. смены: {round(additional_shift_night_hours)}ч × {additional_shift_night_rate:.2f} ₽ = {round(additional_shift_night_hours * additional_shift_night_rate)} ₽"
                                        if additional_shift_night_hours > 0
                                        else None,
                                        f"Праздничные доп. смены: {round(additional_shift_holiday_hours)}ч × {additional_shift_holiday_rate:.2f} ₽ = {round(additional_shift_holiday_hours * additional_shift_holiday_rate)} ₽"
                                        if additional_shift_holiday_hours > 0
                                        else None,
                                        f"Ночные праздничные доп. смены: {round(additional_shift_night_holiday_hours)}ч × {additional_shift_night_holiday_rate:.2f} ₽ = {round(additional_shift_night_holiday_hours * additional_shift_night_holiday_rate)} ₽"
                                        if additional_shift_night_holiday_hours > 0
                                        else None,
                                    ]
                                    if line is not None
                                ]
                            )
                        }

Сумма доп. смен: {format_value(round(additional_shift_salary), " ₽")}</blockquote>'''
                        if additional_shift_salary > 0
                        else ""
                    }

🎁 <b>Премия:</b>
<blockquote expandable>Общий процент премии: {format_percentage(premium.total_premium)}
Общая сумма премии: {format_value(round(premium_amount), " ₽")}
Стоимость 1% премии: ~{
                        round(premium_amount / premium.total_premium)
                        if premium.total_premium and premium.total_premium > 0
                        else 0
                    } ₽

🌟 Показатели:
Оценка: {format_percentage(premium.csi_premium)} = {
                        format_value(round(csi_premium_amount), " ₽")
                    }
FLR: {format_percentage(premium.flr_premium)} = {
                        format_value(round(flr_premium_amount), " ₽")
                    }
ГОК: {format_percentage(premium.gok_premium)} = {
                        format_value(round(gok_premium_amount), " ₽")
                    }
Цель: {format_percentage(premium.target_premium)} = {
                        format_value(round(target_premium_amount), " ₽")
                    }

💼 Дополнительно:
Дисциплина: {format_percentage(premium.discipline_premium)} = {
                        format_value(round(discipline_premium_amount), " ₽")
                    }
Тестирование: {format_percentage(premium.tests_premium)} = {
                        format_value(round(tests_premium_amount), " ₽")
                    }
Благодарности: {format_percentage(premium.thanks_premium)} = {
                        format_value(round(thanks_premium_amount), " ₽")
                    }
Наставничество: {format_percentage(premium.tutors_premium)} = {
                        format_value(round(tutors_premium_amount), " ₽")
                    }
Ручная правка: {format_percentage(premium.head_adjust_premium)} = {
                        format_value(round(head_adjust_premium_amount), " ₽")
                    }</blockquote>

💰 <b>Итого к выплате:</b>
~<b>{format_value(round(total_salary, 1), " ₽")}</b>

<blockquote expandable>⚠️ <b>Важное</b>

Расчет представляет <b>примерную</b> сумму после вычета НДФЛ
Районный коэффициент <b>не участвует в расчете</b>, т.к. примерно покрывает НДФЛ

🧪 <b>Формулы</b>
Обычные часы: часы × ставка
Праздничные часы: часы × ставка × 2
Ночные часы: часы × ставка × 1.2
Ночные праздничные часы: часы × ставка × 2.4
Доп. смены: часы × (ставка × 2.63)

Ночными часами считается локальное время 22:00 - 6:00
Праздничные дни считаются по производственному <a href='https://www.consultant.ru/law/ref/calendar/proizvodstvennye/'>календарю</a></blockquote>

<i>Расчет от: {now.strftime("%d.%m.%y %H:%M")}</i>
<i>Данные премии от: {
                        premium.updated_at.strftime("%d.%m.%y %H:%M")
                        if premium.updated_at
                        else "—"
                    }</i>"""

        except Exception as e:
            logger.error(f"Ошибка при получении KPI для {member.fullname}: {e}")

            # Проверяем, является ли ошибка отсутствием таблицы
            error_str = str(e)
            if "Table" in error_str and "doesn't exist" in error_str:
                message_text = f"""📊 <b>KPI: {member.fullname}</b>

⚠️ <b>Система KPI недоступна</b>

Таблица показателей эффективности не найдена в базе данных.

<i>Обратись к администратору для настройки системы KPI.</i>"""
            else:
                message_text = f"""📊 <b>KPI: {member.fullname}</b>

❌ <b>Ошибка загрузки данных</b>

Произошла ошибка при получении показателей эффективности.

<i>Попробуй позже или обратись к администратору для проверки данных.</i>"""

        await callback.message.edit_text(
            message_text,
            reply_markup=head_member_kpi_kb(member_id, page, action),
        )

    except Exception as e:
        logger.error(f"Ошибка при просмотре KPI участника {member_id}: {e}")
        await callback.answer("❌ Ошибка при получении KPI", show_alert=True)


@head_group_members_router.callback_query(HeadMemberRoleChange.filter())
async def change_member_role(
    callback: CallbackQuery,
    callback_data: HeadMemberRoleChange,
    stp_repo: MainRequestsRepo,
):
    """Обработчик смены роли участника группы"""
    member_id = callback_data.member_id

    try:
        # Поиск участника по ID
        all_users = await stp_repo.employee.get_users()
        member = None
        for user in all_users:
            if user.id == member_id:
                member = user
                break

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
            except TelegramBadRequest as e:
                await callback.answer("Не удалось отправить уведомление специалисту :(")
                logger.error(
                    f"Не удалось отправить уведомление пользователю {member.user_id}: {e}"
                )
        logger.info(
            f"[Руководитель] - [Изменение роли] {callback.from_user.username} ({callback.from_user.id}) изменил роль участника {member_id}: {old_role_name} → {new_role_name}"
        )

        await member_detail_cb(
            callback, HeadMemberDetailMenu(member_id=member.id), stp_repo
        )

    except Exception as e:
        logger.error(f"Ошибка при изменении роли участника {member_id}: {e}")
        await callback.answer("❌ Ошибка при изменении роли", show_alert=True)


@head_group_members_router.callback_query(HeadMemberGameProfileMenu.filter())
async def view_member_game_profile(
    callback: CallbackQuery,
    callback_data: HeadMemberGameProfileMenu,
    stp_repo: MainRequestsRepo,
):
    """Обработчик просмотра игрового профиля участника группы"""
    from tgbot.services.leveling import LevelingSystem

    member_id = callback_data.member_id
    page = callback_data.page

    try:
        # Поиск участника по ID
        all_users = await stp_repo.employee.get_users()
        member = None
        for user in all_users:
            if user.id == member_id:
                member: Employee = user
                break

        if not member:
            await callback.answer("❌ Участник не найден", show_alert=True)
            return

        # Проверяем, что у участника есть user_id (авторизован в боте)
        if not member.user_id:
            await callback.message.edit_text(
                f"""🏮 <b>Игровой профиль</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>

❌ <b>Пользователь не авторизован в боте</b>

<i>Игровой профиль доступен только для авторизованных пользователей</i>""",
                reply_markup=head_member_game_profile_kb(
                    member_id=member.id, page=page
                ),
            )
            return

        # Получаем игровую статистику пользователя
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
            reply_markup=head_member_game_profile_kb(member_id=member.id, page=page),
        )

    except Exception as e:
        logger.error(
            f"Ошибка при получении игрового профиля участника {member_id}: {e}"
        )
        await callback.answer(
            "❌ Ошибка при получении игрового профиля", show_alert=True
        )


@head_group_members_router.callback_query(HeadMemberGameHistoryMenu.filter())
async def view_member_game_history(
    callback: CallbackQuery,
    callback_data: HeadMemberGameHistoryMenu,
    stp_repo: MainRequestsRepo,
):
    """Обработчик просмотра истории транзакций участника группы"""
    member_id = callback_data.member_id
    history_page = callback_data.history_page
    page = callback_data.page

    try:
        # Поиск участника по ID
        all_users = await stp_repo.employee.get_users()
        member = None
        for user in all_users:
            if user.id == member_id:
                member: Employee = user
                break

        if not member:
            await callback.answer("❌ Участник не найден", show_alert=True)
            return

        # Проверяем, что у участника есть user_id (авторизован в боте)
        if not member.user_id:
            await callback.message.edit_text(
                f"""📜 <b>История баланса</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>

❌ <b>Пользователь не авторизован в боте</b>

<i>История баланса доступна только для авторизованных пользователей</i>""",
                reply_markup=head_member_game_history_kb(
                    member_id=member.id, transactions=[], current_page=1, page=page
                ),
            )
            return

        # Получаем транзакции пользователя
        user_transactions = await stp_repo.transaction.get_user_transactions(
            user_id=member.user_id
        )

        if not user_transactions:
            message_text = f"""📜 <b>История баланса</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or ""}

Здесь отображается вся история операций с баллами

У этого участника пока нет транзакций 🙂

<i>Транзакции появляются при покупке предметов, получении достижений и других операциях с баллами</i>"""
        else:
            total_transactions = len(user_transactions)
            message_text = f"""📜 <b>История баланса</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or ""}

Здесь отображается вся история операций с баллами

<i>Всего транзакций: {total_transactions}</i>"""

        await callback.message.edit_text(
            message_text,
            reply_markup=head_member_game_history_kb(
                member_id=member.id,
                transactions=user_transactions,
                current_page=history_page,
                page=page,
            ),
        )

    except Exception as e:
        logger.error(
            f"Ошибка при получении истории транзакций участника {member_id}: {e}"
        )
        await callback.answer(
            "❌ Ошибка при получении истории транзакций", show_alert=True
        )


@head_group_members_router.callback_query(HeadMemberTransactionDetailMenu.filter())
async def view_member_transaction_detail(
    callback: CallbackQuery,
    callback_data: HeadMemberTransactionDetailMenu,
    stp_repo: MainRequestsRepo,
):
    """Обработчик детального просмотра транзакции участника группы"""
    member_id = callback_data.member_id
    transaction_id = callback_data.transaction_id
    history_page = callback_data.history_page
    page = callback_data.page

    try:
        # Поиск участника по ID
        all_users = await stp_repo.employee.get_users()
        member = None
        for user in all_users:
            if user.id == member_id:
                member = user
                break

        if not member:
            await callback.answer("❌ Участник не найден", show_alert=True)
            return

        # Получаем информацию о транзакции
        transaction = await stp_repo.transaction.get_transaction(transaction_id)

        if not transaction:
            await callback.message.edit_text(
                f"""📊 <b>Детали транзакции</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>

❌ Не смог найти информацию о транзакции""",
                reply_markup=head_member_transaction_detail_kb(
                    member_id=member_id, history_page=history_page, page=page
                ),
            )
            return

        # Определяем эмодзи и текст типа операции
        type_emoji = "➕" if transaction.type == "earn" else "➖"
        type_text = "Начисление" if transaction.type == "earn" else "Списание"

        # Определяем источник транзакции
        source_names = {
            "achievement": "🏆 Достижение",
            "product": "🛒 Покупка предмета",
            "manual": "✍️ Ручная операция",
            "casino": "🎰 Казино",
        }
        source_name = source_names.get(transaction.source_type, "❓ Неизвестно")
        if transaction.source_type == "achievement" and transaction.source_id:
            achievement = await stp_repo.achievement.get_achievement(
                transaction.source_id
            )
            match achievement.period:
                case "d":
                    source_name = "🏆 Ежедневное достижение: " + achievement.name
                case "w":
                    source_name = "🏆 Еженедельное достижение: " + achievement.name
                case "m":
                    source_name = "🏆 Ежемесячное достижение: " + achievement.name

        # Формируем сообщение с подробной информацией
        message_text = f"""📊 <b>Детали транзакции</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or ""}

<b>📈 Операция</b>
{type_emoji} {type_text} <b>{transaction.amount}</b> баллов

<b>🔢 ID:</b> <code>{transaction.id}</code>

<b>📍 Источник</b>
{source_name}

<b>📅 Дата создания</b>
{transaction.created_at.strftime("%d.%m.%Y в %H:%M")}"""

        if transaction.comment:
            message_text += f"\n\n<b>💬 Комментарий</b>\n<blockquote expandable>{transaction.comment}</blockquote>"

        await callback.message.edit_text(
            message_text,
            reply_markup=head_member_transaction_detail_kb(
                member_id=member_id, history_page=history_page, page=page
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка при получении деталей транзакции {transaction_id}: {e}")
        await callback.answer(
            "❌ Ошибка при получении деталей транзакции", show_alert=True
        )

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import HeadFilter
from tgbot.handlers.user.schedule.main import schedule_service
from tgbot.keyboards.head.group.main import GroupManagementMenu
from tgbot.keyboards.head.group.members import (
    HeadGroupMembersMenu,
    HeadMemberActionMenu,
    HeadMemberDetailMenu,
    HeadMemberScheduleMenu,
    HeadMemberScheduleNavigation,
    get_month_name_by_index,
    head_group_members_kb,
    head_member_detail_kb,
    head_member_schedule_kb,
)

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

У вас пока нет подчиненных в системе.
            
<i>Если это ошибка, обратитесь к администратору.</i>""",
            reply_markup=head_group_members_kb([], current_page=1),
        )
        return

    # Показываем первую страницу по умолчанию
    total_members = len(group_members)

    message_text = f"""👥 <b>Состав группы</b>

Участники твоей группы: <b>{total_members}</b>

🔒 - не авторизован в боте

<i>Нажмите на участника для просмотра подробной информации</i>"""

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

🔒 - не авторизован в боте

<i>Нажмите на участника для просмотра подробной информации</i>"""

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
<b>Email:</b> {member.email or "Не указано"}"""

    # Добавляем статус только для неавторизованных пользователей
    if not member.user_id:
        message_text += "\n<b>Статус:</b> 🔒 Не авторизован в боте"

    message_text += "\n\n<i>Выберите действие:</i>"

    await callback.message.edit_text(
        message_text,
        reply_markup=head_member_detail_kb(member.id, callback_data.page),
        parse_mode="HTML",
    )


@head_group_members_router.callback_query(HeadMemberActionMenu.filter())
async def member_action_cb(
    callback: CallbackQuery,
    callback_data: HeadMemberActionMenu,
    stp_repo: MainRequestsRepo,
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

    elif callback_data.action == "kpi":
        message_text = f"""📊 <b>KPI: {member.fullname}</b>

<i>Функция в разработке</i>

Здесь будут отображены показатели эффективности выбранного сотрудника."""

    else:
        await callback.answer("❌ Неизвестное действие", show_alert=True)
        return

    await callback.message.edit_text(
        message_text,
        reply_markup=head_member_detail_kb(member.id, callback_data.page),
    )


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
            # Получаем расписание участника (компактный формат)
            schedule_response = await schedule_service.get_user_schedule_response(
                user=member, month=current_month, compact=True
            )

            await callback.message.edit_text(
                f"""📅 <b>Расписание участника</b>

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
            error_message = "❌ Расписание для данного сотрудника не найдено"
            if "не найден" in str(schedule_error).lower():
                error_message = f"❌ Сотрудник {member.fullname} не найден в расписании"
            elif "файл" in str(schedule_error).lower():
                error_message = "❌ Файл расписания недоступен"

            await callback.message.edit_text(
                f"""📅 <b>Расписание участника</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or "Не указано"}

{error_message}

<i>Возможно, сотрудник не включен в текущее расписание или файл недоступен.</i>""",
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
            # Получаем расписание участника
            schedule_response = await schedule_service.get_user_schedule_response(
                user=member, month=month_to_display, compact=compact
            )

            await callback.message.edit_text(
                f"""📅 <b>Расписание участника</b>

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
            error_message = "❌ Расписание для данного сотрудника не найдено"
            if "не найден" in str(schedule_error).lower():
                error_message = f"❌ Сотрудник {member.fullname} не найден в расписании"
            elif "файл" in str(schedule_error).lower():
                error_message = "❌ Файл расписания недоступен"

            await callback.message.edit_text(
                f"""📅 <b>Расписание участника</b>

<b>ФИО:</b> <a href="https://t.me/{member.username}">{member.fullname}</a>
<b>Должность:</b> {member.position or "Не указано"} {member.division or "Не указано"}

{error_message}

<i>Возможно, сотрудник не включен в текущее расписание или файл недоступен.</i>""",
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

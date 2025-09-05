from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import Employee
from tgbot.filters.role import HeadFilter
from tgbot.handlers.head.schedule.group import head_group_schedule_service
from tgbot.handlers.user.schedule.main import schedule_service
from tgbot.keyboards.head.group.main import GroupManagementMenu
from tgbot.keyboards.user.schedule.main import get_yekaterinburg_date, group_schedule_kb

head_group_schedule_router = Router()
head_group_schedule_router.message.filter(F.chat.type == "private", HeadFilter())
head_group_schedule_router.callback_query.filter(
    F.message.chat.type == "private", HeadFilter()
)


@head_group_schedule_router.callback_query(
    GroupManagementMenu.filter(F.menu == "schedule")
)
async def group_mgmt_schedule_cb(callback: CallbackQuery, user: Employee, stp_repo):
    """Обработчик расписания группы из меню управления"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    try:
        current_date = get_yekaterinburg_date()

        # Получаем групповое расписание для руководителя
        (
            text,
            total_pages,
            has_prev,
            has_next,
        ) = await head_group_schedule_service.get_group_schedule_for_head(
            user, current_date, 1, stp_repo
        )

        await callback.message.edit_text(
            text=text,
            reply_markup=group_schedule_kb(
                current_date=current_date,
                page=1,
                total_pages=total_pages,
                has_prev=has_prev,
                has_next=has_next,
                user_type="head",
                from_group_mgmt=True,
            ),
        )

    except Exception as e:
        await schedule_service.handle_schedule_error(callback, e)

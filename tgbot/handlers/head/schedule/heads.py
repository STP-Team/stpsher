import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import Employee
from tgbot.filters.role import HeadFilter
from tgbot.keyboards.common.schedule import (
    HeadNavigation,
    ScheduleMenu,
    get_yekaterinburg_date,
    heads_kb,
)
from tgbot.services.schedule.schedule_handlers import schedule_service

logger = logging.getLogger(__name__)

head_schedule_head_router = Router()
head_schedule_head_router.message.filter(F.chat.type == "private", HeadFilter())
head_schedule_head_router.callback_query.filter(
    F.message.chat.type == "private", HeadFilter()
)


@head_schedule_head_router.callback_query(ScheduleMenu.filter(F.menu == "heads"))
async def heads_schedule(callback: CallbackQuery, user: Employee, stp_repo):
    """Обработчик расписания руководителей групп"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    try:
        current_date = get_yekaterinburg_date()
        heads_text = await schedule_service.get_heads_response(
            division=user.division, date=current_date, stp_repo=stp_repo
        )

        await callback.message.edit_text(
            text=heads_text,
            reply_markup=heads_kb(current_date),
        )

    except Exception as e:
        await schedule_service.handle_schedule_error(callback, e)


@head_schedule_head_router.callback_query(HeadNavigation.filter())
async def handle_head_navigation(
    callback: CallbackQuery, callback_data: HeadNavigation, user: Employee, stp_repo
):
    """Обработчик навигации по руководителям групп"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    try:
        action = callback_data.action

        if action == "-":
            await callback.answer()
            return

        # Определяем целевую дату
        if action == "today":
            target_date = get_yekaterinburg_date()
        else:
            target_date = schedule_service.parse_date_from_callback(callback_data.date)

        # Получаем данные руководителей групп
        heads_text = await schedule_service.get_heads_response(
            division=user.division, date=target_date, stp_repo=stp_repo
        )

        await callback.message.edit_text(
            text=heads_text,
            reply_markup=heads_kb(target_date),
        )
        await callback.answer()

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

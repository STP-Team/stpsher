import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from stp_database import Employee

from tgbot.handlers.user.schedule.main import schedule_service
from tgbot.keyboards.user.schedule.main import (
    DutyNavigation,
    ScheduleMenu,
    duties_kb,
    get_yekaterinburg_date,
)

logger = logging.getLogger(__name__)

user_schedule_duty_router = Router()
user_schedule_duty_router.message.filter(F.chat.type == "private")
user_schedule_duty_router.callback_query.filter(F.message.chat.type == "private")


@user_schedule_duty_router.callback_query(ScheduleMenu.filter(F.menu == "duties"))
async def duties_schedule(callback: CallbackQuery, user: Employee, stp_repo):
    """Обработчик расписания дежурных"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    try:
        current_date = get_yekaterinburg_date()
        duties_text = await schedule_service.get_duties_response(
            division=user.division, date=current_date, stp_repo=stp_repo
        )

        await callback.message.edit_text(
            text=duties_text,
            reply_markup=duties_kb(current_date),
        )

    except Exception as e:
        await schedule_service.handle_schedule_error(callback, e)


@user_schedule_duty_router.callback_query(DutyNavigation.filter())
async def handle_duty_navigation(
    callback: CallbackQuery, callback_data: DutyNavigation, user: Employee, stp_repo
):
    """Обработчик навигации по дежурствам"""
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

        # Получаем данные дежурных
        duties_text = await schedule_service.get_duties_response(
            division=user.division, date=target_date, stp_repo=stp_repo
        )

        await callback.message.edit_text(
            text=duties_text, reply_markup=duties_kb(target_date)
        )
        await callback.answer()

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

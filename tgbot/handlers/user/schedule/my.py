import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import User
from tgbot.handlers.user.schedule.main import schedule_service
from tgbot.keyboards.user.schedule.main import (
    MonthNavigation,
    ScheduleMenu,
    create_detailed_schedule_keyboard,
    schedule_with_month_kb,
)

logger = logging.getLogger(__name__)

user_schedule_my_router = Router()
user_schedule_my_router.message.filter(F.chat.type == "private")
user_schedule_my_router.callback_query.filter(F.message.chat.type == "private")


@user_schedule_my_router.callback_query(ScheduleMenu.filter(F.menu == "my"))
async def user_schedule(callback: CallbackQuery, user: User):
    """Обработчик личного расписания"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    try:
        month = schedule_service.get_current_month()
        schedule_text = await schedule_service.get_user_schedule_response(
            user=user, month=month, compact=True
        )

        await callback.message.edit_text(
            text=schedule_text,
            reply_markup=schedule_with_month_kb(
                current_month=month, schedule_type="my"
            ),
        )

    except Exception as e:
        await schedule_service.handle_schedule_error(callback, e)


@user_schedule_my_router.callback_query(MonthNavigation.filter(F.action == "compact"))
async def handle_compact_view(callback: CallbackQuery, user: User):
    """Обработчик перехода к компактному виду"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    callback_data = MonthNavigation.unpack(callback.data)
    current_month = callback_data.current_month
    schedule_type = callback_data.schedule_type

    try:
        schedule_text = await schedule_service.get_user_schedule_response(
            user=user, month=current_month, compact=True
        )

        await callback.message.edit_text(
            text=schedule_text,
            reply_markup=schedule_with_month_kb(
                current_month=current_month, schedule_type=schedule_type
            ),
        )
        await callback.answer()

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@user_schedule_my_router.callback_query(MonthNavigation.filter())
async def handle_month_navigation(
    callback: CallbackQuery, callback_data: MonthNavigation, user: User
):
    """Обработчик навигации по месяцам"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    action = callback_data.action
    current_month = callback_data.current_month
    schedule_type = callback_data.schedule_type

    try:
        if action in ["prev", "next"]:
            # Компактный режим для навигации
            schedule_text = await schedule_service.get_user_schedule_response(
                user=user, month=current_month, compact=True
            )

            await callback.message.edit_text(
                text=schedule_text,
                reply_markup=schedule_with_month_kb(
                    current_month=current_month, schedule_type=schedule_type
                ),
            )

        elif action == "detailed":
            # Детальный режим
            schedule_text = await schedule_service.get_user_schedule_response(
                user=user, month=current_month, compact=False
            )

            keyboard = create_detailed_schedule_keyboard(current_month, schedule_type)
            await callback.message.edit_text(
                text=schedule_text,
                reply_markup=keyboard,
            )

        await callback.answer()

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

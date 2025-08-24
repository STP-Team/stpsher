import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import User
from tgbot.filters.role import HeadFilter
from tgbot.handlers.user.schedule.main import schedule_service
from tgbot.keyboards.user.main import MainMenu
from tgbot.keyboards.user.schedule.main import (
    schedule_kb,
)

logger = logging.getLogger(__name__)

head_schedule_router = Router()
head_schedule_router.message.filter(F.chat.type == "private", HeadFilter())
head_schedule_router.callback_query.filter(
    F.message.chat.type == "private", HeadFilter()
)


@head_schedule_router.callback_query(MainMenu.filter(F.menu == "schedule"))
async def schedule(callback: CallbackQuery, user: User):
    """Главное меню расписаний"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    await callback.message.edit_text(
        """📅 Меню графиков""",
        reply_markup=schedule_kb(),
    )

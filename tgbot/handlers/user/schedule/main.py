import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import Employee
from tgbot.keyboards.common.schedule import schedule_kb
from tgbot.keyboards.user.main import MainMenu
from tgbot.services.schedule.schedule_handlers import schedule_service

logger = logging.getLogger(__name__)

user_schedule_router = Router()
user_schedule_router.message.filter(F.chat.type == "private")
user_schedule_router.callback_query.filter(F.message.chat.type == "private")


@user_schedule_router.callback_query(MainMenu.filter(F.menu == "schedule"))
async def schedule(callback: CallbackQuery, user: Employee):
    """Главное меню расписаний"""
    if not await schedule_service.check_user_auth(callback, user):
        return

    await callback.message.edit_text(
        """<b>📅 Меню графиков</b>
        
Здесь ты найдешь все, что связано с графиками""",
        reply_markup=schedule_kb(),
    )

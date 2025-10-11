import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from stp_database import Employee

from tgbot.filters.role import GokFilter
from tgbot.keyboards.gok.main import gok_kb
from tgbot.keyboards.user.main import MainMenu

gok_router = Router()
gok_router.message.filter(F.chat.type == "private", GokFilter())
gok_router.callback_query.filter(F.message.chat.type == "private", GokFilter())

logger = logging.getLogger(__name__)


@gok_router.message(CommandStart())
async def gok_start_cmd(message: Message, user: Employee):
    await message.answer(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

Здесь ты можешь:
• Просматривать список достижений
• Просматривать список предметов
• Активировать покупки специалистов""",
        reply_markup=gok_kb(),
    )
    logger.info(
        f"[ГОК] - [Главное меню] {message.from_user.username} ({message.from_user.id}): Открыто главное меню"
    )


@gok_router.callback_query(MainMenu.filter(F.menu == "main"))
async def gok_start_cb(callback: CallbackQuery, user: Employee):
    await callback.message.edit_text(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

Здесь ты можешь:
• Просматривать список достижений
• Просматривать список предметов
• Активировать покупки специалистов""",
        reply_markup=gok_kb(),
    )

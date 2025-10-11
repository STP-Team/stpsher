from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from stp_database import Employee

from tgbot.filters.role import RootFilter
from tgbot.keyboards.admin.main import main_kb
from tgbot.keyboards.user.main import MainMenu

root_router = Router()
root_router.message.filter(F.chat.type == "private", RootFilter())
root_router.callback_query.filter(F.message.chat.type == "private", RootFilter())


@root_router.message(CommandStart())
async def admin_start_cmd(message: Message, user: Employee):
    await message.answer(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

Здесь ты можешь управлять основными функциями бота""",
        reply_markup=main_kb(),
    )


@root_router.callback_query(MainMenu.filter(F.menu == "main"))
async def admin_start_cb(callback: CallbackQuery, user: Employee):
    await callback.message.edit_text(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

Здесь ты можешь управлять основными функциями бота""",
        reply_markup=main_kb(),
    )

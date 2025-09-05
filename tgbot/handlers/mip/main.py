from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models import Employee
from tgbot.filters.role import MipFilter
from tgbot.keyboards.mip.main import main_kb
from tgbot.keyboards.user.main import MainMenu

mip_router = Router()
mip_router.message.filter(F.chat.type == "private", MipFilter())
mip_router.callback_query.filter(F.message.chat.type == "private", MipFilter())


@mip_router.message(CommandStart())
async def mip_start_cmd(message: Message, user: Employee):
    await message.answer(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

Здесь ты можешь загружать графики, обучения, менять учетки спецов, а так же активировать покупки специалистов""",
        reply_markup=main_kb(),
    )


@mip_router.callback_query(MainMenu.filter(F.menu == "main"))
async def mip_start_cb(callback: CallbackQuery, user: Employee):
    await callback.message.edit_text(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

Здесь ты можешь загружать графики, обучения, менять учетки спецов, а так же активировать покупки специалистов""",
        reply_markup=main_kb(),
    )

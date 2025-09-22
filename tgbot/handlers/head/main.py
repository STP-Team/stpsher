from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.utils.deep_linking import create_startgroup_link

from infrastructure.database.models import Employee
from tgbot.filters.role import HeadFilter
from tgbot.keyboards.head.main import main_kb
from tgbot.keyboards.user.main import MainMenu

head_router = Router()
head_router.message.filter(F.chat.type == "private", HeadFilter())
head_router.callback_query.filter(F.message.chat.type == "private", HeadFilter())


@head_router.message(CommandStart())
async def admin_start_cmd(message: Message, user: Employee):
    group_link = await create_startgroup_link(message.bot, payload="start")
    await message.answer(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП
Здесь ты можешь найти графики, показатели своей группы и многое другое""",
        reply_markup=main_kb(group_link),
    )


@head_router.callback_query(MainMenu.filter(F.menu == "main"))
async def user_start_cb(callback: CallbackQuery, user: Employee):
    group_link = await create_startgroup_link(callback.bot, payload="start")
    await callback.message.edit_text(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП
Здесь ты можешь найти графики, показатели своей группы и многое другое""",
        reply_markup=main_kb(group_link),
    )

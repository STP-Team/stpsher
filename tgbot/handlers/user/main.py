from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models import User
from tgbot.keyboards.user.main import MainMenu, auth_kb, main_kb

user_router = Router()
user_router.message.filter(F.chat.type == "private")
user_router.callback_query.filter(F.message.chat.type == "private")


@user_router.message(CommandStart())
async def user_start_cmd(message: Message, user: User):
    if not user:
        await message.answer(
            """👋 Привет

Я - бот-помощник СТП

Используй кнопку ниже для авторизации""",
            reply_markup=auth_kb(),
        )
        return

    await message.answer(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник специалистов СТП
Здесь ты можешь найти графики, достижения и многое другое

<i>Используй меню для выбора действия</i>""",
        reply_markup=main_kb(),
    )


@user_router.callback_query(MainMenu.filter(F.menu == "main"))
async def user_start_cb(callback: CallbackQuery, user: User):
    if not user:
        await callback.message.edit_text(
            """👋 Привет

Я - бот-помощник СТП

Используй кнопку ниже для авторизации""",
            reply_markup=auth_kb(),
        )
        return

    await callback.message.edit_text(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник специалистов СТП
Здесь ты можешь найти графики, достижения и многое другое

<i>Используй меню для выбора действия</i>""",
        reply_markup=main_kb(),
    )

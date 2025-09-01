from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models import User
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.keyboards.user.main import MainMenu, auth_kb, main_kb
from tgbot.services.leveling import LevelingSystem

user_router = Router()
user_router.message.filter(F.chat.type == "private")
user_router.callback_query.filter(F.message.chat.type == "private")


@user_router.message(CommandStart())
async def user_start_cmd(message: Message, user: User, stp_repo: MainRequestsRepo):
    if not user:
        await message.answer(
            """👋 Привет

Я - бот-помощник СТП

Используй кнопку ниже для авторизации""",
            reply_markup=auth_kb(),
        )
        return

    user_balance = await stp_repo.transaction.get_user_balance(user_id=user.user_id)
    achievements_sum = await stp_repo.transaction.get_user_achievements_sum(
        user_id=user.user_id
    )
    awards_sum = await stp_repo.user_award.get_user_awards_sum(user_id=user.user_id)
    level_info_text = LevelingSystem.get_level_info_text(achievements_sum, user_balance)

    await message.answer(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

{level_info_text}

<blockquote expandable><b>📊 Баланс</b>
Всего заработано: {achievements_sum} баллов
Всего потрачено: {awards_sum} баллов</blockquote>""",
        reply_markup=main_kb(),
    )


@user_router.callback_query(MainMenu.filter(F.menu == "main"))
async def user_start_cb(
    callback: CallbackQuery, user: User, stp_repo: MainRequestsRepo
):
    if not user:
        await callback.message.edit_text(
            """👋 Привет

Я - бот-помощник СТП

Используй кнопку ниже для авторизации""",
            reply_markup=auth_kb(),
        )
        return

    user_balance = await stp_repo.transaction.get_user_balance(user_id=user.user_id)
    achievements_sum = await stp_repo.transaction.get_user_achievements_sum(
        user_id=user.user_id
    )
    awards_sum = await stp_repo.user_award.get_user_awards_sum(user_id=user.user_id)
    level_info_text = LevelingSystem.get_level_info_text(achievements_sum, user_balance)

    await callback.message.edit_text(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

{level_info_text}

<blockquote expandable><b>📊 Баланс</b>
Всего заработано: {achievements_sum} баллов
Всего потрачено: {awards_sum} баллов</blockquote>""",
        reply_markup=main_kb(),
    )

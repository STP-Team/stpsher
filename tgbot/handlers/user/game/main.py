from aiogram import F, Router
from aiogram.types import CallbackQuery
from stp_database import Employee
from stp_database.repo.STP.requests import MainRequestsRepo

from tgbot.keyboards.user.game.main import game_kb
from tgbot.keyboards.user.main import MainMenu, auth_kb
from tgbot.services.leveling import LevelingSystem

user_game_router = Router()
user_game_router.message.filter(F.chat.type == "private")
user_game_router.callback_query.filter(F.message.chat.type == "private")


@user_game_router.callback_query(MainMenu.filter(F.menu == "game"))
async def game_main(
    callback: CallbackQuery, user: Employee, stp_repo: MainRequestsRepo
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
    purchases_sum = await stp_repo.purchase.get_user_purchases_sum(user_id=user.user_id)
    level_info_text = LevelingSystem.get_level_info_text(achievements_sum, user_balance)

    await callback.message.edit_text(
        f"""🏮 <b>Игровой профиль</b>

{level_info_text}

<blockquote expandable><b>✨ Баланс</b>
Всего заработано: {achievements_sum} баллов
Всего потрачено: {purchases_sum} баллов</blockquote>""",
        reply_markup=game_kb(user),
    )

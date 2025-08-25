from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models import User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.keyboards.user.main import MainMenu, auth_kb, main_kb

user_router = Router()
user_router.message.filter(F.chat.type == "private")
user_router.callback_query.filter(F.message.chat.type == "private")


@user_router.message(CommandStart())
async def user_start_cmd(message: Message, user: User, stp_repo: RequestsRepo):
    if not user:
        await message.answer(
            """👋 Привет

Я - бот-помощник СТП

Используй кнопку ниже для авторизации""",
            reply_markup=auth_kb(),
        )
        return

    user_achievements = await stp_repo.user_achievement.get_user_achievements(
        user.user_id
    )
    user_awards = await stp_repo.user_award.get_user_awards(user.user_id)
    achievements_sum = await stp_repo.user_achievement.get_user_achievements_sum(
        user_id=user.user_id
    )
    awards_sum = await stp_repo.user_award.get_user_awards_sum(user_id=user.user_id)

    # Новые методы для получения самых частых
    most_frequent_achievement = (
        await stp_repo.user_achievement.get_most_frequent_achievement(
            user_id=user.user_id
        )
    )
    most_used_award = await stp_repo.user_award.get_most_used_award(
        user_id=user.user_id
    )

    # Формируем текст для самого частого достижения
    if most_frequent_achievement:
        achievement_text = (
            f"{most_frequent_achievement[0]} ({most_frequent_achievement[1]}x)"
        )
    else:
        achievement_text = "Нет достижений"

    # Формируем текст для самой частой награды
    if most_used_award:
        award_text = f"{most_used_award[0]} ({most_used_award[1]}x)"
    else:
        award_text = "Нет наград"

    # TODO Улучшить формулу расчета уровня
    await message.answer(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник специалистов СТП

<b>⚔️ Твой уровень:</b> {round(achievements_sum / 100)}
<b>✨ Кол-во баллов:</b> {achievements_sum - awards_sum} баллов

<blockquote><b>📊 Баланс</b>
Всего заработано: {achievements_sum} баллов
Всего потрачено: {awards_sum} баллов

<b>🎯 Достижения</b>
<b>Всего получено:</b> {len(user_achievements)}
<b>Самое частое:</b> {achievement_text}

<b>🏅 Награды</b>
<b>Всего куплено:</b> {len(user_awards)}
<b>Самая частая:</b> {award_text}</blockquote>""",
        reply_markup=main_kb(),
    )


@user_router.callback_query(MainMenu.filter(F.menu == "main"))
async def user_start_cb(callback: CallbackQuery, user: User, stp_repo: RequestsRepo):
    if not user:
        await callback.message.edit_text(
            """👋 Привет

Я - бот-помощник СТП

Используй кнопку ниже для авторизации""",
            reply_markup=auth_kb(),
        )
        return

    user_achievements = await stp_repo.user_achievement.get_user_achievements(
        user.user_id
    )
    user_awards = await stp_repo.user_award.get_user_awards(user.user_id)
    achievements_sum = await stp_repo.user_achievement.get_user_achievements_sum(
        user_id=user.user_id
    )
    awards_sum = await stp_repo.user_award.get_user_awards_sum(user_id=user.user_id)

    # Новые методы для получения самых частых
    most_frequent_achievement = (
        await stp_repo.user_achievement.get_most_frequent_achievement(
            user_id=user.user_id
        )
    )
    most_used_award = await stp_repo.user_award.get_most_used_award(
        user_id=user.user_id
    )

    # Формируем текст для самого частого достижения
    if most_frequent_achievement:
        achievement_text = (
            f"{most_frequent_achievement[0]} ({most_frequent_achievement[1]}x)"
        )
    else:
        achievement_text = "Нет достижений"

    # Формируем текст для самой частой награды
    if most_used_award:
        award_text = f"{most_used_award[0]} ({most_used_award[1]}x)"
    else:
        award_text = "Нет наград"

    # TODO Улучшить формулу расчета уровня
    await callback.message.edit_text(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник специалистов СТП

<b>⚔️ Твой уровень:</b> {round(achievements_sum / 100)}
<b>✨ Кол-во баллов:</b> {achievements_sum - awards_sum} баллов

<blockquote><b>📊 Баланс</b>
Всего заработано: {achievements_sum} баллов
Всего потрачено: {awards_sum} баллов

<b>🎯 Достижения</b>
<b>Всего получено:</b> {len(user_achievements)}
<b>Самое частое:</b> {achievement_text}

<b>🏅 Награды</b>
<b>Всего куплено:</b> {len(user_awards)}
<b>Самая частая:</b> {award_text}</blockquote>""",
        reply_markup=main_kb(),
    )

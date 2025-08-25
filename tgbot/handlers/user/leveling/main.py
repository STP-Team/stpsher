import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.keyboards.user.leveling.main import leveling_kb
from tgbot.keyboards.user.main import MainMenu

user_leveling_router = Router()
user_leveling_router.message.filter(
    F.chat.type == "private",
)
user_leveling_router.callback_query.filter(F.message.chat.type == "private")

logger = logging.getLogger(__name__)


@user_leveling_router.callback_query(MainMenu.filter(F.menu == "leveling"))
async def user_leveling_cb(callback: CallbackQuery, user: User, stp_repo: RequestsRepo):
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
        f"""<b>🏆 Ачивки</b>

<b>⚔️ Твой уровень:</b> {round(achievements_sum / 100)}
<b>✨ Кол-во баллов:</b> {achievements_sum - awards_sum} баллов

<blockquote><b>📊Статистика</b>
Всего заработано: {achievements_sum} баллов
Всего потрачено: {awards_sum} баллов

Получено достижений: {len(user_achievements)}
Активировано наград: {len(user_awards)}

<b>🎯 Самое частое достижение:</b> {achievement_text}
<b>🏅 Самая частая награда:</b> {award_text}</blockquote>""",
        reply_markup=leveling_kb(),
    )


# @user_achievements_router.callback_query(AwardsMenu.filter(F.menu == "awards_all"))
# async def awards_all(
#     callback: CallbackQuery, callback_data: AwardsMenu, stp_repo: RequestsRepo
# ):
#     """
#     Обработчик клика на меню всех возможных наград
#     """
#
#     # Достаём номер страницы из callback data, стандартно = 1
#     page = getattr(callback_data, "page", 1)
#
#     all_awards = await stp_repo.award.get_awards()
#     logger.info(all_awards)
#
#     # Логика пагинации
#     awards_per_page = 5
#     total_awards = len(all_awards)
#     total_pages = (total_awards + awards_per_page - 1) // awards_per_page
#
#     # Считаем начало и конец текущей страницы - ИСПРАВЛЕНО!
#     start_idx = (page - 1) * awards_per_page  # Используем переменную page
#     end_idx = start_idx + awards_per_page
#     page_awards = all_awards[start_idx:end_idx]
#
#     # Построение списка наград для текущей страницы
#     awards_list = []
#     for counter, award in enumerate(page_awards, start=start_idx + 1):
#         awards_list.append(f"""{counter}. <b>{award.name}</b>
# 💵 Стоимость: {award.cost}
# 📝 Описание: {award.description}
# 🔰 Направление: {award.division}""")
#         if award.count > 0:
#             awards_list.append(f"""🧮 Активаций: {award.count}""")
#         awards_list.append("")
#
#     message_text = f"""<b>🏆 Все возможные награды</b>
# <i>Страница {page} из {total_pages}</i>
#
# <blockquote expandable>Всего наград:
# НТП: {sum(1 for award in all_awards if award.division == "НТП")}
# НЦК: {sum(1 for award in all_awards if award.division == "НЦК")}</blockquote>
#
# {"\n".join(awards_list)}"""
#
#     await callback.message.edit_text(
#         message_text, reply_markup=awards_paginated_kb(page, total_pages)
#     )
#     logger.info(
#         f"[Пользователь] - [Меню] {callback.from_user.username} ({callback.from_user.id}): Открыто меню всех наград, страница {page}"
#     )

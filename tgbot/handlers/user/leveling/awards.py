import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.keyboards.mip.leveling.main import LevelingMenu
from tgbot.keyboards.user.leveling.main import (
    AwardsMenu,
    awards_kb,
    awards_paginated_kb,
)

user_leveling_awards_router = Router()
user_leveling_awards_router.message.filter(
    F.chat.type == "private",
)
user_leveling_awards_router.callback_query.filter(F.message.chat.type == "private")

logger = logging.getLogger(__name__)


@user_leveling_awards_router.callback_query(LevelingMenu.filter(F.menu == "awards"))
async def user_awards_cb(callback: CallbackQuery, stp_repo: RequestsRepo):
    user_awards_sum = await stp_repo.user_award.get_user_awards_sum(
        user_id=callback.from_user.id
    )
    logger.info(user_awards_sum)

    await callback.message.edit_text(
        """<b>👏 Награды</b>

Здесь ты можешь найти доступные для приобретения, а так же все возможные награды

<i>Используй меню для выбора действия</i>""",
        reply_markup=awards_kb(),
    )


@user_leveling_awards_router.callback_query(AwardsMenu.filter(F.menu == "all"))
async def awards_all(
    callback: CallbackQuery,
    user: User,
    callback_data: AwardsMenu,
    stp_repo: RequestsRepo,
):
    """
    Обработчик клика на меню всех возможных наград
    """

    # Достаём номер страницы из callback data, стандартно = 1
    page = getattr(callback_data, "page", 1)

    all_awards = await stp_repo.award.get_awards(
        division="НТП" if "НТП" in user.division else "НЦК"
    )

    # Логика пагинации
    awards_per_page = 5
    total_awards = len(all_awards)
    total_pages = (total_awards + awards_per_page - 1) // awards_per_page

    # Считаем начало и конец текущей страницы
    start_idx = (page - 1) * awards_per_page  # Используем переменную page
    end_idx = start_idx + awards_per_page
    page_awards = all_awards[start_idx:end_idx]

    # Построение списка наград для текущей страницы
    awards_list = []
    for counter, award in enumerate(page_awards, start=start_idx + 1):
        awards_list.append(f"""{counter}. <b>{award.name}</b>
💵 Стоимость: {award.cost}
📝 Описание: {award.description}""")
        if award.count > 0:
            awards_list.append(f"""🧮 Активаций: {award.count}""")
        awards_list.append("")

    message_text = f"""<b>🏆 Все возможные награды</b>
<i>Страница {page} из {total_pages}</i>

{"\n".join(awards_list)}"""

    await callback.message.edit_text(
        message_text, reply_markup=awards_paginated_kb(page, total_pages)
    )
    logger.info(
        f"[Пользователь] - [Меню] {callback.from_user.username} ({callback.from_user.id}): Открыто меню всех наград, страница {page}"
    )

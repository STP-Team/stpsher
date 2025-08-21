import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.repo.requests import RequestsRepo
from tgbot.filters.role import MipFilter
from tgbot.keyboards.mip.leveling.main import (
    achievements_kb,
    awards_paginated_kb,
    AwardsMenu,
)
from tgbot.keyboards.user.main import MainMenu

mip_leveling_router = Router()
mip_leveling_router.message.filter(F.chat.type == "private", MipFilter())
mip_leveling_router.callback_query.filter(F.message.chat.type == "private", MipFilter())

logger = logging.getLogger(__name__)


@mip_leveling_router.callback_query(MainMenu.filter(F.menu == "leveling"))
async def mip_achievements_cmd(callback: CallbackQuery):
    await callback.message.edit_text(
        """<b>🏆 Достижения</b>

Используй меню для просмотра управления достижениями

<b>💪 Твои возможности</b>
- Подтверждение/отмена наград
- Просмотр списка достижений
- Просмотр списка наград

<i>Используй меню для выбора действия</i>""",
        reply_markup=achievements_kb(),
    )


@mip_leveling_router.callback_query(AwardsMenu.filter(F.menu == "awards_all"))
async def awards_all(
    callback: CallbackQuery, callback_data: AwardsMenu, stp_repo: RequestsRepo
):
    """
    Обработчик клика на меню всех возможных наград
    """

    # Достаём номер страницы из callback data, стандартно = 1
    page = getattr(callback_data, "page", 1)

    all_awards = await stp_repo.award.get_awards()
    logger.info(all_awards)

    # Логика пагинации
    awards_per_page = 5
    total_awards = len(all_awards)
    total_pages = (total_awards + awards_per_page - 1) // awards_per_page

    # Считаем начало и конец текущей страницы - ИСПРАВЛЕНО!
    start_idx = (page - 1) * awards_per_page  # Используем переменную page
    end_idx = start_idx + awards_per_page
    page_awards = all_awards[start_idx:end_idx]

    # Построение списка наград для текущей страницы
    awards_list = []
    for counter, award in enumerate(page_awards, start=start_idx + 1):
        awards_list.append(f"""{counter}. <b>{award.name}</b>
💵 Стоимость: {award.cost}
📝 Описание: {award.description}
🔰 Направление: {award.division}""")
        if award.count > 0:
            awards_list.append(f"""🧮 Активаций: {award.count}""")
        awards_list.append("")

    message_text = f"""<b>🏆 Все возможные награды</b>
<i>Страница {page} из {total_pages}</i>

<blockquote expandable>Всего наград:
НТП: {sum(1 for award in all_awards if award.division == "НТП")}
НЦК: {sum(1 for award in all_awards if award.division == "НЦК")}</blockquote>

{"\n".join(awards_list)}"""

    await callback.message.edit_text(
        message_text, reply_markup=awards_paginated_kb(page, total_pages)
    )
    logger.info(
        f"[Пользователь] - [Меню] {callback.from_user.username} ({callback.from_user.id}): Открыто меню всех наград, страница {page}"
    )

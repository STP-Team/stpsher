import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import MipFilter
from tgbot.keyboards.mip.game.achievements import achievements_paginated_kb
from tgbot.keyboards.mip.game.main import (
    GameMenu,
    parse_filters,
)

mip_game_achievements_router = Router()
mip_game_achievements_router.message.filter(F.chat.type == "private", MipFilter())
mip_game_achievements_router.callback_query.filter(
    F.message.chat.type == "private", MipFilter()
)

logger = logging.getLogger(__name__)


def filter_items_by_division(items, active_filters):
    """Filter achievements or products by division based on active filters"""
    # Filter by specific divisions
    filtered_items = []
    for item in items:
        if item.division in active_filters:
            filtered_items.append(item)

    return filtered_items


@mip_game_achievements_router.callback_query(
    GameMenu.filter(F.menu == "achievements_all")
)
async def achievements_all(
    callback: CallbackQuery, callback_data: GameMenu, stp_repo: MainRequestsRepo
):
    """
    Обработчик клика на меню всех возможных достижений для МИП
    МИП видит все достижения из всех направлений с возможностью фильтрации
    """

    # Достаём параметры из callback data
    page = getattr(callback_data, "page", 1)
    filters = getattr(callback_data, "filters", "НЦК,НТП")

    # Парсим активные фильтры
    active_filters = parse_filters(filters)

    # Получаем ВСЕ достижения без фильтрации по направлению
    all_achievements = await stp_repo.achievement.get_achievements()

    # Применяем фильтрацию
    filtered_achievements = filter_items_by_division(all_achievements, active_filters)

    # Логика пагинации
    achievements_per_page = 5
    total_achievements = len(filtered_achievements)
    total_pages = (
        total_achievements + achievements_per_page - 1
    ) // achievements_per_page

    # Считаем начало и конец текущей страницы
    start_idx = (page - 1) * achievements_per_page
    end_idx = start_idx + achievements_per_page
    page_achievements = filtered_achievements[start_idx:end_idx]

    # Построение списка достижений для текущей страницы
    achievements_list = []
    for counter, achievement in enumerate(page_achievements, start=start_idx + 1):
        # Экранируем HTML символы в полях
        description = (
            str(achievement.description).replace("<", "&lt;").replace(">", "&gt;")
        )
        name = str(achievement.name).replace("<", "&lt;").replace(">", "&gt;")
        division = str(achievement.division).replace("<", "&lt;").replace(">", "&gt;")
        position = str(achievement.position).replace("<", "&lt;").replace(">", "&gt;")

        achievements_list.append(f"""{counter}. <b>{name}</b>
<blockquote>🏅 Награда: {achievement.reward} баллов
📝 Описание: {description}
🔰 Должность: {position} {division}</blockquote>""")
        achievements_list.append("")

    # Создаем статистику по всем достижениям (не только отфильтрованным)
    stats_ntp = sum(
        1 for achievement in all_achievements if achievement.division == "НТП"
    )
    stats_nck = sum(
        1 for achievement in all_achievements if achievement.division == "НЦК"
    )

    # Статистика по отфильтрованным
    filtered_stats = f"Показано: {total_achievements}"

    message_text = f"""<b>🎯 Все возможные достижения</b>

<blockquote>Всего достижений:
НТП: {stats_ntp} | НЦК: {stats_nck}
{filtered_stats}</blockquote>

{chr(10).join(achievements_list)}"""

    await callback.message.edit_text(
        message_text, reply_markup=achievements_paginated_kb(page, total_pages, filters)
    )
    logger.info(
        f"[МИП] - [Меню] {callback.from_user.username} ({callback.from_user.id}): Открыто меню всех достижений, страница {page}, фильтры: {filters}"
    )

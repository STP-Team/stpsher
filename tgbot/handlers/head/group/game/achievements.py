import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from stp_database.repo.STP.requests import MainRequestsRepo

from tgbot.filters.role import HeadFilter
from tgbot.handlers.gok.game.main import filter_items_by_division
from tgbot.keyboards.head.group.game.achievements import head_achievements_paginated_kb
from tgbot.keyboards.head.group.game.main import HeadGameMenu
from tgbot.keyboards.mip.game.main import (
    FilterToggleMenu,
    GameMenu,
    parse_filters,
    toggle_filter,
)

head_game_achievements_router = Router()
head_game_achievements_router.message.filter(F.chat.type == "private", HeadFilter())
head_game_achievements_router.callback_query.filter(
    F.message.chat.type == "private", HeadFilter()
)

logger = logging.getLogger(__name__)


@head_game_achievements_router.callback_query(
    HeadGameMenu.filter(F.menu == "achievements")
)
async def head_achievements_menu(callback: CallbackQuery, stp_repo: MainRequestsRepo):
    """
    Обработчик клика на меню достижений - перенаправляет на achievements_all с дефолтными параметрами
    """
    # Создаем callback_data с дефолтными параметрами
    from tgbot.keyboards.mip.game.main import GameMenu

    new_callback_data = GameMenu(menu="achievements_all", page=1, filters="НЦК,НТП")

    # Вызываем основной обработчик
    await head_achievements_all(callback, new_callback_data, stp_repo)


@head_game_achievements_router.callback_query(
    GameMenu.filter(F.menu == "achievements_all")
)
async def head_achievements_all(
    callback: CallbackQuery, callback_data: GameMenu, stp_repo: MainRequestsRepo
):
    """
    Обработчик клика на меню всех возможных достижений для руководителей
    Руководители видят все достижения из всех направлений с возможностью фильтрации
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
        message_text,
        reply_markup=head_achievements_paginated_kb(page, total_pages, filters),
    )
    logger.info(
        f"[Руководитель] - [Достижения] {callback.from_user.username} ({callback.from_user.id}): Просмотр достижений, страница {page}, фильтры: {filters}"
    )


@head_game_achievements_router.callback_query(
    FilterToggleMenu.filter(F.menu == "achievements_all")
)
async def head_achievements_toggle_filter(
    callback: CallbackQuery, callback_data: FilterToggleMenu, stp_repo: MainRequestsRepo
):
    """Обработчик переключения фильтров для достижений"""
    menu = callback_data.menu
    filter_name = callback_data.filter_name
    current_filters = callback_data.current_filters

    # Переключаем фильтр
    new_filters = toggle_filter(current_filters, filter_name)

    # Переходим на первую страницу при изменении фильтров
    if menu == "achievements_all":
        await head_achievements_all(
            callback,
            GameMenu(menu="achievements_all", page=1, filters=new_filters),
            stp_repo,
        )

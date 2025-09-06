import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import HeadFilter
from tgbot.handlers.gok.game.main import filter_items_by_division
from tgbot.keyboards.gok.main import GokFilterToggleMenu, parse_filters, toggle_filter
from tgbot.keyboards.head.group.game.achievements import head_achievements_paginated_kb
from tgbot.keyboards.head.group.game.products import head_products_paginated_kb

head_game_filters_router = Router()
head_game_filters_router.message.filter(F.chat.type == "private", HeadFilter())
head_game_filters_router.callback_query.filter(
    F.message.chat.type == "private", HeadFilter()
)

logger = logging.getLogger(__name__)


@head_game_filters_router.callback_query(GokFilterToggleMenu.filter())
async def head_toggle_filter(
    callback: CallbackQuery,
    callback_data: GokFilterToggleMenu,
    stp_repo: MainRequestsRepo,
):
    """
    Обработчик переключения фильтров для руководителей
    """
    menu = callback_data.menu
    filter_name = callback_data.filter_name
    current_filters = callback_data.current_filters
    page = callback_data.page

    # Переключаем фильтр
    new_filters = toggle_filter(current_filters, filter_name)

    if menu == "achievements_all":
        # Получаем достижения и применяем фильтрацию
        active_filters = parse_filters(new_filters)
        all_achievements = await stp_repo.achievement.get_achievements()
        filtered_achievements = filter_items_by_division(
            all_achievements, active_filters
        )

        # Логика пагинации
        achievements_per_page = 5
        total_achievements = len(filtered_achievements)
        total_pages = (
            total_achievements + achievements_per_page - 1
        ) // achievements_per_page

        # Проверяем, что текущая страница не выходит за границы
        if page > total_pages:
            page = 1

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
            division = (
                str(achievement.division).replace("<", "&lt;").replace(">", "&gt;")
            )
            position = (
                str(achievement.position).replace("<", "&lt;").replace(">", "&gt;")
            )

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
<i>Страница {page} из {total_pages}</i>

<blockquote>Всего достижений:
НТП: {stats_ntp} | НЦК: {stats_nck}
{filtered_stats}</blockquote>

{chr(10).join(achievements_list)}"""

        await callback.message.edit_text(
            message_text,
            reply_markup=head_achievements_paginated_kb(page, total_pages, new_filters),
        )

    elif menu == "products_all":
        # Получаем предметы и применяем фильтрацию
        active_filters = parse_filters(new_filters)
        all_products = await stp_repo.product.get_products()
        filtered_products = filter_items_by_division(all_products, active_filters)

        # Логика пагинации
        products_per_page = 5
        total_products = len(filtered_products)
        total_pages = (total_products + products_per_page - 1) // products_per_page

        # Проверяем, что текущая страница не выходит за границы
        if page > total_pages:
            page = 1

        # Считаем начало и конец текущей страницы
        start_idx = (page - 1) * products_per_page
        end_idx = start_idx + products_per_page
        page_products = filtered_products[start_idx:end_idx]

        # Построение списка предметов для текущей страницы
        products_list = []
        for counter, product in enumerate(page_products, start=start_idx + 1):
            product_text = f"""
<b>{counter}. {product.name}</b>
<blockquote>📍 Активаций: {product.count}
💵 Стоимость: {product.cost} баллов
🔰 Направление: {product.division}
📝 Описание: {product.description}</blockquote>"""
            products_list.append(product_text)

        # Статистика
        stats_ntp = sum(1 for product in all_products if product.division == "НТП")
        stats_nck = sum(1 for product in all_products if product.division == "НЦК")
        filtered_stats = f"Показано: {total_products}"

        message_text = f"""
<b>👏 Все возможные предметы</b>
<i>Страница {page} из {total_pages}</i>

<blockquote expandable><b>Всего предметов:</b>  
• НТП: {stats_ntp}  
• НЦК: {stats_nck}  
{filtered_stats}
</blockquote>{chr(10).join(products_list)}
        """

        await callback.message.edit_text(
            message_text,
            reply_markup=head_products_paginated_kb(page, total_pages, new_filters),
        )

    logger.info(
        f"[Руководитель] - [Фильтр] {callback.from_user.username} ({callback.from_user.id}): Применен фильтр {filter_name} для {menu}"
    )

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import HeadFilter
from tgbot.handlers.gok.game.main import filter_items_by_division
from tgbot.keyboards.gok.main import GokProductsMenu, parse_filters
from tgbot.keyboards.head.game.products import head_products_paginated_kb

head_game_products_router = Router()
head_game_products_router.message.filter(F.chat.type == "private", HeadFilter())
head_game_products_router.callback_query.filter(
    F.message.chat.type == "private", HeadFilter()
)

logger = logging.getLogger(__name__)


@head_game_products_router.callback_query(
    GokProductsMenu.filter(F.menu == "products_all")
)
async def head_products_all(
    callback: CallbackQuery, callback_data: GokProductsMenu, stp_repo: MainRequestsRepo
):
    """
    Обработчик клика на меню всех возможных предметов для руководителей
    Руководители видят все предметы из всех направлений с возможностью фильтрации
    """

    # Достаём параметры из callback data
    page = getattr(callback_data, "page", 1)
    filters = getattr(callback_data, "filters", "НЦК,НТП")

    # Парсим активные фильтры
    active_filters = parse_filters(filters)

    # Получаем ВСЕ предметы без фильтрации по направлению
    all_products = await stp_repo.product.get_products()

    # Применяем фильтрацию
    filtered_products = filter_items_by_division(all_products, active_filters)

    # Логика пагинации
    products_per_page = 5
    total_products = len(filtered_products)
    total_pages = (total_products + products_per_page - 1) // products_per_page

    # Считаем начало и конец текущей страницы
    start_idx = (page - 1) * products_per_page
    end_idx = start_idx + products_per_page
    page_products = filtered_products[start_idx:end_idx]

    # Построение списка предметов для текущей страницы
    products_list = []
    for counter, product in enumerate(page_products, start=start_idx + 1):
        product_text = f"""
<b>{counter}. {product.name}</b>
📍 Активаций: {product.count}
💵 Стоимость: {product.cost} баллов
🔰 Направление: {product.division}
📝 Описание: {product.description}"""
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
        reply_markup=head_products_paginated_kb(page, total_pages, filters),
    )
    logger.info(
        f"[Руководитель] - [Предметы] {callback.from_user.username} ({callback.from_user.id}): Просмотр предметов, страница {page}, фильтры: {filters}"
    )

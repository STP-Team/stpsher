from typing import List

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.gok.main import (
    GokGameMenu,
    GokProductsMenu,
    GokPurchaseActionMenu,
    GokPurchaseActivationMenu,
    create_filters_row,
)
from tgbot.keyboards.user.main import MainMenu


def gok_purchases_paginated_kb(
    page: int, total_pages: int, filters: str
) -> InlineKeyboardMarkup:
    """
    Клавиатура с пагинацией для списка покупок ГОК
    :param page: Текущая страница
    :param total_pages: Всего страниц
    :param filters: Активные фильтры
    :return:
    """
    buttons = []

    # Add filter buttons
    filter_buttons = create_filters_row("products_all", filters, page)
    if filter_buttons:
        buttons.append(filter_buttons)

    # Pagination controls
    nav_buttons = []

    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=GokProductsMenu(
                    menu="products_all", page=page - 1, filters=filters
                ).pack(),
            )
        )

    nav_buttons.append(
        InlineKeyboardButton(
            text=f"📄 {page}/{total_pages}",
            callback_data="current_page",
        )
    )

    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=GokProductsMenu(
                    menu="products_all", page=page + 1, filters=filters
                ).pack(),
            )
        )

    buttons.append(nav_buttons)

    # Back button
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def gok_products_activation_kb(
    page: int, total_pages: int, page_products: List
) -> InlineKeyboardMarkup:
    """
    Клавиатура для меню активации покупок ГОК
    :param page: Текущая страница
    :param total_pages: Всего страниц
    :param page_products: Список покупок на текущей странице
    :return:
    """
    buttons = []

    # Purchases buttons for current page
    for i, product_details in enumerate(page_products):
        purchase = product_details.purchase
        product = product_details.product_info

        # Truncate name for button display
        display_name = (
            (product.name[:25] + "...") if len(product.name) > 28 else product.name
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{i + 1}. {display_name}",
                    callback_data=GokPurchaseActivationMenu(
                        purchase_id=purchase.id, page=page
                    ).pack(),
                )
            ]
        )

    # Pagination controls
    if total_pages > 1:
        nav_buttons = []

        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=GokGameMenu(
                        menu="products_activation", page=page - 1
                    ).pack(),
                )
            )

        nav_buttons.append(
            InlineKeyboardButton(
                text=f"{page}/{total_pages}",
                callback_data="noop",
            )
        )

        if page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=GokGameMenu(
                        menu="products_activation", page=page + 1
                    ).pack(),
                )
            )

        buttons.append(nav_buttons)

    # Back button
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def gok_purchases_detail_kb(
    purchase_id: int, current_page: int
) -> InlineKeyboardMarkup:
    """
    Клавиатура для детального просмотра покупки с возможностью подтверждения/отклонения
    :param purchase_id: ID покупки пользователя
    :param current_page: Текущая страница в списке покупок
    :return:
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=GokPurchaseActionMenu(
                    purchase_id=purchase_id, action="approve", page=current_page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=GokPurchaseActionMenu(
                    purchase_id=purchase_id, action="reject", page=current_page
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="⬅️",
                callback_data=GokGameMenu(
                    menu="products_activation", page=current_page
                ).pack(),
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

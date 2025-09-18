from typing import List

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infrastructure.database.repo.STP.purchase import PurchaseDetailedParams
from tgbot.keyboards.mip.game.main import (
    GameMenu,
    ProductsMenu,
    PurchaseActionMenu,
    PurchaseActivationMenu,
    create_filters_row,
)
from tgbot.keyboards.user.main import MainMenu


def purchase_activation_kb(
    current_page: int,
    total_pages: int,
    page_purchases: List[PurchaseDetailedParams] = None,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для списка покупок, ожидающих активации
    """
    buttons = []

    # Добавляем кнопки для выбора покупок (максимум 2 в ряд)
    if page_purchases:
        # Вычисляем стартовый индекс для нумерации на текущей странице
        start_idx = (current_page - 1) * 5  # 5 покупок на страницу

        for i in range(0, len(page_purchases), 2):
            purchase_row = []

            # Первая покупка в ряду
            first_purchase = page_purchases[i]
            first_purchase_number = start_idx + i + 1
            purchase_row.append(
                InlineKeyboardButton(
                    text=f"{first_purchase_number}. {first_purchase.product_info.name}",
                    callback_data=PurchaseActivationMenu(
                        purchase_id=first_purchase.user_purchase.id, page=current_page
                    ).pack(),
                )
            )

            # Вторая покупка в ряду (если есть)
            if i + 1 < len(page_purchases):
                second_purchase = page_purchases[i + 1]
                second_purchase_number = start_idx + i + 2
                purchase_row.append(
                    InlineKeyboardButton(
                        text=f"{second_purchase_number}. {second_purchase.product_info.name}",
                        callback_data=PurchaseActivationMenu(
                            purchase_id=second_purchase.user_purchase.id,
                            page=current_page,
                        ).pack(),
                    )
                )

            buttons.append(purchase_row)

    # Пагинация
    if total_pages > 1:
        pagination_row = []

        # Первая кнопка (⏪ или пусто)
        if current_page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=GameMenu(menu="products_activation", page=1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Вторая кнопка (⬅️ или пусто)
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=GameMenu(
                        menu="products_activation", page=current_page - 1
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Центральная кнопка - Индикатор страницы
        pagination_row.append(
            InlineKeyboardButton(
                text=f"{current_page}/{total_pages}",
                callback_data="noop",
            )
        )

        # Четвертая кнопка (➡️ или пусто)
        if current_page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=GameMenu(
                        menu="products_activation", page=current_page + 1
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Пятая кнопка (⏭️ или пусто)
        if current_page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏭️",
                    callback_data=GameMenu(
                        menu="products_activation", page=total_pages
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Навигация
    navigation_row = [
        InlineKeyboardButton(
            text="↩️ Назад", callback_data=MainMenu(menu="main").pack()
        ),
    ]
    buttons.append(navigation_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def purchase_detail_kb(purchase_id: int, current_page: int) -> InlineKeyboardMarkup:
    """
    Клавиатура детального просмотра покупки для МИП с возможностью подтверждения/отклонения
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=PurchaseActionMenu(
                    purchase_id=purchase_id, action="approve", page=current_page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=PurchaseActionMenu(
                    purchase_id=purchase_id, action="reject", page=current_page
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=GameMenu(
                    menu="products_activation", page=current_page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def purchase_paginated_kb(
    current_page: int, total_pages: int, filters: str = "НЦК,НТП"
) -> InlineKeyboardMarkup:
    """
    Клавиатура пагинации для всех возможных покупок с фильтрами
    """
    buttons = []

    # Пагинация
    if total_pages > 1:
        pagination_row = []

        # Первая кнопка (⏪ или пусто)
        if current_page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=ProductsMenu(
                        menu="products_all", page=1, filters=filters
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Вторая кнопка (⬅️ или пусто)
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=ProductsMenu(
                        menu="products_all", page=current_page - 1, filters=filters
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Центральная кнопка - Индикатор страницы (всегда видна)
        pagination_row.append(
            InlineKeyboardButton(
                text=f"{current_page}/{total_pages}",
                callback_data="noop",
            )
        )

        # Четвертая кнопка (➡️ или пусто)
        if current_page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=ProductsMenu(
                        menu="products_all", page=current_page + 1, filters=filters
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Пятая кнопка (⏭️ или пусто)
        if current_page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏭️",
                    callback_data=ProductsMenu(
                        menu="products_all", page=total_pages, filters=filters
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Добавляем ряд фильтров
    filter_buttons = create_filters_row("products_all", filters, current_page)
    buttons.append(filter_buttons)  # Все фильтры в одной строке

    # Навигация
    navigation_row = [
        InlineKeyboardButton(
            text="↩️ Назад", callback_data=MainMenu(menu="game").pack()
        ),
        InlineKeyboardButton(
            text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
        ),
    ]
    buttons.append(navigation_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def purchase_notify_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура меню МИП для уведомления о новой покупке на активацию
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✍️ Активация предметов",
                callback_data=GameMenu(menu="products_activation").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🏠 Главное меню", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard

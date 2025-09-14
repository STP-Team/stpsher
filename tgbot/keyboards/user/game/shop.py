from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.game.inventory import UseProductMenu
from tgbot.keyboards.user.game.main import GameMenu
from tgbot.keyboards.user.main import MainMenu


class ShopMenu(CallbackData, prefix="shop"):
    menu: str = "available"
    page: int = 1
    product_id: int = 0


class ShopBuy(CallbackData, prefix="shop_buy"):
    product_id: int
    page: int = 1


class ShopConfirm(CallbackData, prefix="shop_confirm"):
    product_id: int
    page: int = 1
    action: str  # "buy" or "back"


class ProductDetailsShop(CallbackData, prefix="product_details_shop"):
    user_product_id: int


class SellProductShopMenu(CallbackData, prefix="sell_product"):
    user_product_id: int
    source_menu: str = "shop"


def shop_kb(
    current_page: int,
    total_pages: int,
    page_products: list = None,
    filter_type: str = "available",
    user_balance: int = 0,
) -> InlineKeyboardMarkup:
    """
    Клавиатура пагинации предметов с фильтрацией
    """
    buttons = []

    # Добавляем кнопки для выбора предметов (максимум 2 в ряд)
    if page_products:
        # Вычисляем стартовый индекс для нумерации на текущей странице
        start_idx = (current_page - 1) * 5  # 5 предметов на страницу

        for i in range(0, len(page_products), 2):
            product_row = []

            # Первый предмет в ряду
            first_product = page_products[i]
            first_product_number = start_idx + i + 1
            # Добавляем иконку если предмет доступен для покупки
            balance_icon = "💰" if user_balance >= first_product.cost else ""
            product_row.append(
                InlineKeyboardButton(
                    text=f"{first_product_number}. {balance_icon}{first_product.name}",
                    callback_data=ShopBuy(
                        product_id=first_product.id, page=current_page
                    ).pack(),
                )
            )

            # Второй предмет в ряду (если есть)
            if i + 1 < len(page_products):
                second_product = page_products[i + 1]
                second_product_number = start_idx + i + 2
                # Добавляем иконку если предмет доступен для покупки
                balance_icon = "💰" if user_balance >= second_product.cost else ""
                product_row.append(
                    InlineKeyboardButton(
                        text=f"{second_product_number}. {balance_icon}{second_product.name}",
                        callback_data=ShopBuy(
                            product_id=second_product.id, page=current_page
                        ).pack(),
                    )
                )

            buttons.append(product_row)

    # Пагинация
    if total_pages > 1:
        pagination_row = []

        # Первая кнопка (⏪ или пусто)
        if current_page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=ShopMenu(menu=filter_type, page=1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Вторая кнопка (⬅️ или пусто)
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=ShopMenu(
                        menu=filter_type, page=current_page - 1
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
                    callback_data=ShopMenu(
                        menu=filter_type, page=current_page + 1
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
                    callback_data=ShopMenu(menu=filter_type, page=total_pages).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Добавляем кнопки фильтрации
    filter_row = [
        InlineKeyboardButton(
            text=f"Только доступные {'✅' if filter_type == 'available' else ''}",
            callback_data=ShopMenu(menu="available", page=1).pack(),
        ),
        InlineKeyboardButton(
            text=f"Все предметы {'✅' if filter_type == 'all' else ''}",
            callback_data=ShopMenu(menu="all", page=1).pack(),
        ),
    ]
    buttons.append(filter_row)

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


def to_game_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура для возврата в игровой профиль
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="game").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard


def product_confirmation_kb(product_id: int, current_page: int) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения покупки предмета
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Купить",
                callback_data=ShopConfirm(
                    product_id=product_id, page=current_page, action="buy"
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=ShopMenu(menu="available", page=current_page).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_purchase_success_kb(user_product_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура после успешной покупки предмета
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🎯 Использовать",
                callback_data=UseProductMenu(user_product_id=user_product_id).pack(),
            ),
            InlineKeyboardButton(
                text="💸 Вернуть",
                callback_data=SellProductShopMenu(
                    user_product_id=user_product_id, source_menu="shop"
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🎒 Инвентарь",
                callback_data=GameMenu(menu="inventory").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🛒 Магазин",
                callback_data=ShopMenu(menu="available", page=1).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

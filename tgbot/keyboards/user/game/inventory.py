from typing import List

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import Sequence

from infrastructure.database.repo.STP.purchase import PurchaseDetailedParams
from infrastructure.database.models.STP.transactions import Transaction
from tgbot.keyboards.user.game.main import GameMenu
from tgbot.keyboards.user.main import MainMenu


class InventoryHistoryMenu(CallbackData, prefix="inventory_history"):
    menu: str = "inventory"
    page: int = 1


class ProductDetailMenu(CallbackData, prefix="product_detail"):
    user_product_id: int


class UseProductMenu(CallbackData, prefix="use_product"):
    user_product_id: int


class SellProductMenu(CallbackData, prefix="sell_product_inventory"):
    user_product_id: int
    source_menu: str = "inventory"


class CancelActivationMenu(CallbackData, prefix="cancel_activation"):
    user_product_id: int


def get_status_emoji(status: str) -> str:
    """Возвращает эмодзи в зависимости от статуса"""
    status_emojis = {
        "stored": "📦",
        "review": "⏳",
        "used_up": "🔒",
        "canceled": "🔥",
        "rejected": "⛔",
    }
    return status_emojis.get(status, "❓")


def inventory_kb(
    user_products: List[PurchaseDetailedParams],
    current_page: int = 1,
    products_per_page: int = 8,
) -> InlineKeyboardMarkup:
    """
    Клавиатура инвентаря с пагинацией.
    Отображает 2 предмета в ряд, по умолчанию 8 предметов на страницу (4 ряда).
    """
    buttons = []

    # Рассчитываем пагинацию
    total_products = len(user_products)
    total_pages = (total_products + products_per_page - 1) // products_per_page

    # Рассчитываем диапазон предметов для текущей страницы
    start_idx = (current_page - 1) * products_per_page
    end_idx = start_idx + products_per_page
    page_products = user_products[start_idx:end_idx]

    # Создаем кнопки для предметов (2 в ряд)
    for i in range(0, len(page_products), 2):
        row = []

        # Первый предмет в ряду
        product_detail = page_products[i]
        user_product = product_detail.user_purchase
        product_info = product_detail.product_info

        date_str = user_product.bought_at.strftime("%d.%m.%y")
        status_emoji = get_status_emoji(user_product.status)
        usage_info = f"({product_detail.current_usages}/{product_detail.max_usages})"
        button_text = f"{status_emoji} {usage_info} {product_info.name} ({date_str})"

        row.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=ProductDetailMenu(user_product_id=user_product.id).pack(),
            )
        )

        # Второй предмет в ряду (если есть)
        if i + 1 < len(page_products):
            product_detail = page_products[i + 1]
            user_product = product_detail.user_purchase
            product_info = product_detail.product_info

            date_str = user_product.bought_at.strftime("%d.%m.%y")
            status_emoji = get_status_emoji(user_product.status)
            usage_info = (
                f"({product_detail.current_usages}/{product_detail.max_usages})"
            )
            button_text = (
                f"{status_emoji} {usage_info} {product_info.name} ({date_str})"
            )

            row.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=ProductDetailMenu(
                        user_product_id=user_product.id
                    ).pack(),
                )
            )

        buttons.append(row)

    # Добавляем пагинацию (только если больше одной страницы)
    if total_pages > 1:
        pagination_row = []

        # Клавиатура пагинации: [⏪] [⬅️] [страница] [➡️] [⏭️]

        # Первая кнопка (⏪ или пусто)
        if current_page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=InventoryHistoryMenu(menu="inventory", page=1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Вторая кнопка (⬅️ или пусто)
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=InventoryHistoryMenu(
                        menu="inventory", page=current_page - 1
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
                    callback_data=InventoryHistoryMenu(
                        menu="inventory", page=current_page + 1
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
                    callback_data=InventoryHistoryMenu(
                        menu="inventory", page=total_pages
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Добавляем кнопки навигации
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="game").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def to_game_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура для возврата в игровой профиль
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="💎 Магазин",
                callback_data=GameMenu(menu="shop").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="game").pack()
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard


def product_detail_kb(
    user_product_id: int,
    can_use: bool = False,
    can_sell: bool = False,
    can_cancel: bool = False,
    source_menu: str = "inventory",
) -> InlineKeyboardMarkup:
    """Клавиатура детального просмотра предмета"""
    buttons = []

    if can_use:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🎯 Использовать",
                    callback_data=UseProductMenu(
                        user_product_id=user_product_id
                    ).pack(),
                )
            ]
        )

    if can_sell:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="💸 Вернуть",
                    callback_data=SellProductMenu(
                        user_product_id=user_product_id, source_menu=source_menu
                    ).pack(),
                )
            ]
        )

    if can_cancel:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✋🏻 Отменить активацию",
                    callback_data=CancelActivationMenu(
                        user_product_id=user_product_id
                    ).pack(),
                )
            ]
        )

    # Context-aware back button
    if source_menu == "shop":
        from tgbot.keyboards.user.game.shop import ShopMenu

        back_callback = ShopMenu(menu="available", page=1).pack()
    else:
        back_callback = GameMenu(menu="inventory").pack()

    buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data=back_callback)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

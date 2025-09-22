from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.game.main import GameMenu
from tgbot.keyboards.user.main import MainMenu


class DutyPurchaseActivationMenu(CallbackData, prefix="duty_purchase_activation"):
    purchase_id: int
    page: int


class DutyPurchaseActionMenu(CallbackData, prefix="duty_purchase_action"):
    purchase_id: int
    action: str
    page: int


def duty_products_activation_kb(
    page: int, total_pages: int, purchases: list
) -> InlineKeyboardMarkup:
    """
    Клавиатура для активации предметов дежурными
    """
    buttons = []

    # Добавляем кнопки для каждой покупки
    for i, purchase_details in enumerate(purchases, start=1):
        purchase = purchase_details.user_purchase
        product = purchase_details.product_info

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{i}. {product.name[:20]}{'...' if len(product.name) > 20 else ''}",
                    callback_data=DutyPurchaseActivationMenu(
                        purchase_id=purchase.id, page=page
                    ).pack(),
                )
            ]
        )

    # Навигация по страницам
    nav_buttons = []
    if total_pages > 1:
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=GameMenu(menu="products_activation").pack(),
                )
            )
        if page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=GameMenu(menu="products_activation").pack(),
                )
            )

    if nav_buttons:
        buttons.append(nav_buttons)

    # Кнопка возврата
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=MainMenu(menu="game").pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def duty_purchases_detail_kb(purchase_id: int, page: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для детального просмотра покупки и действий с ней
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=DutyPurchaseActionMenu(
                    purchase_id=purchase_id, action="approve", page=page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=DutyPurchaseActionMenu(
                    purchase_id=purchase_id, action="reject", page=page
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=GameMenu(menu="products_activation").pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

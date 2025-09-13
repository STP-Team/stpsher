from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infrastructure.database.models.STP.employee import Employee
from tgbot.keyboards.user.main import MainMenu
from tgbot.misc.dicts import executed_codes


class GameMenu(CallbackData, prefix="game"):
    menu: str


def game_kb(user: Employee = None) -> InlineKeyboardMarkup:
    """
    Клавиатура игрового меню.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = []

    # Add products activation button for duties (role 3) as first row
    if user and user.role == executed_codes["Дежурный"]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✍️ Активация предметов",
                    callback_data=GameMenu(menu="products_activation").pack(),
                ),
            ]
        )

    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="💎 Магазин",
                    callback_data=GameMenu(menu="shop").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎒 Инвентарь",
                    callback_data=GameMenu(menu="inventory").pack(),
                ),
                InlineKeyboardButton(
                    text="🎲 Казино",
                    callback_data=GameMenu(menu="casino").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎯 Достижения",
                    callback_data=GameMenu(menu="achievements").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📜 История баланса",
                    callback_data=GameMenu(menu="history").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="↩️ Назад", callback_data=MainMenu(menu="main").pack()
                ),
            ],
        ]
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard

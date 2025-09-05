from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.main import MainMenu


class GameMenu(CallbackData, prefix="game"):
    menu: str


def game_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура игрового меню.

    :return: Объект встроенной клавиатуры для возврата главного меню
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

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard

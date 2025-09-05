from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.gok.main import GokGameMenu, GokProductsMenu
from tgbot.keyboards.user.main import MainMenu


def head_game_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура игрового меню для руководителей
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🎯 Достижения",
                callback_data=GokGameMenu(menu="achievements_all").pack(),
            ),
            InlineKeyboardButton(
                text="👏 Предметы",
                callback_data=GokProductsMenu(menu="products_all").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=MainMenu(menu="group_management").pack(),
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard

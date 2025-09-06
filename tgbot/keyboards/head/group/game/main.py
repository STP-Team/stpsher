from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.main import MainMenu


class HeadGroupStatsMenu(CallbackData, prefix="head_group_stats"):
    menu: str


class HeadGameMenu(CallbackData, prefix="head_game"):
    menu: str
    page: int = 1
    filters: str = "НЦК,НТП"  # Фильтры по направлению


def head_game_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура игрового меню для руководителей
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🎯 Достижения",
                callback_data=HeadGameMenu(menu="achievements").pack(),
            ),
            InlineKeyboardButton(
                text="👏 Предметы",
                callback_data=HeadGameMenu(menu="products").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="📜 История группы",
                callback_data=HeadGameMenu(menu="history").pack(),
            ),
            InlineKeyboardButton(
                text="📊 Рейтинг",
                callback_data=HeadGameMenu(menu="ranking").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=MainMenu(menu="group_management").pack(),
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

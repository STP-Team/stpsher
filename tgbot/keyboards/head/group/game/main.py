from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.gok.main import GokGameMenu, GokProductsMenu
from tgbot.keyboards.head.group.game.history import (
    HeadGroupHistoryMenu,
    HeadRankingMenu,
)
from tgbot.keyboards.user.main import MainMenu


class HeadGroupStatsMenu(CallbackData, prefix="head_group_stats"):
    menu: str


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
                text="📜 История группы",
                callback_data=HeadGroupHistoryMenu(menu="history").pack(),
            ),
            InlineKeyboardButton(
                text="📊 Рейтинг",
                callback_data=HeadRankingMenu(menu="ranking").pack(),
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

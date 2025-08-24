from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.mip.leveling.main import LevelingMenu
from tgbot.keyboards.user.main import MainMenu


class AchievementsMenu(CallbackData, prefix="achievements"):
    menu: str


def leveling_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура меню достижений.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🎯 Достижения",
                callback_data=LevelingMenu(menu="achievements").pack(),
            ),
            InlineKeyboardButton(
                text="👏 Награды",
                callback_data=LevelingMenu(menu="awards").pack(),
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


def achievements_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура меню достижений.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🔎 Детализация",
                callback_data=AchievementsMenu(menu="details").pack(),
            ),
            InlineKeyboardButton(
                text="🏆 Все возможные",
                callback_data=AchievementsMenu(menu="all").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="leveling").pack()
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

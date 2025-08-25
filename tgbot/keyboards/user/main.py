from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class MainMenu(CallbackData, prefix="menu"):
    menu: str


def auth_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура авторизации.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(text="🔑 Авторизация", callback_data="auth"),
        ]
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )

    return keyboard


def main_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура главного меню.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="📅 Графики", callback_data=MainMenu(menu="schedule").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="🎯 Достижения",
                callback_data=MainMenu(menu="achievements").pack(),
            ),
            InlineKeyboardButton(
                text="👏 Награды",
                callback_data=MainMenu(menu="awards").pack(),
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard

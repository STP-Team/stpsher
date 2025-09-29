from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


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

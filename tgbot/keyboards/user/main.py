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
            InlineKeyboardButton(
                text="🌟 Показатели", callback_data=MainMenu(menu="kpi").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="🏮 Игровой профиль",
                callback_data=MainMenu(menu="game").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🕵🏻 Поиск сотрудника",
                callback_data=MainMenu(menu="search").pack(),
            ),
            InlineKeyboardButton(
                text="👯‍♀️ Группы",
                callback_data=MainMenu(menu="groups").pack(),
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard


def ok_kb() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="👌 Хорошо",
                callback_data=MainMenu(menu="main").pack(),
            )
        ],
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard

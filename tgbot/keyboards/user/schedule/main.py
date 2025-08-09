from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from tgbot.keyboards.user.main import MainMenu


class ScheduleMenu(CallbackData, prefix="schedule_menu"):
    menu: str


def schedule_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура меню графиков.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="👔 Мой график", callback_data=ScheduleMenu(menu="my").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="👮‍♂️ Старшие", callback_data=ScheduleMenu(menu="duties").pack()
            ),
            InlineKeyboardButton(
                text="👑 РГ", callback_data=ScheduleMenu(menu="heads").pack()
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

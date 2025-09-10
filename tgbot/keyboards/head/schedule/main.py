# tgbot/keyboards/head/main.py (обновить существующий файл)

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.main import MainMenu
from tgbot.keyboards.user.schedule.main import ScheduleMenu


def schedule_kb_head() -> InlineKeyboardMarkup:
    """
    Клавиатура меню графиков для руководителей (с дополнительными опциями).

    :return: Объект встроенной клавиатуры для меню графиков руководителя
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="📋 Мой график",
                callback_data=ScheduleMenu(menu="my").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🚨 Дежурные",
                callback_data=ScheduleMenu(menu="duties").pack(),
            ),
            InlineKeyboardButton(
                text="👑 Руководители",
                callback_data=ScheduleMenu(menu="heads").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="❤️ Моя группа",
                callback_data=ScheduleMenu(menu="group").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

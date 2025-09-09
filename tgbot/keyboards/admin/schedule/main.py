from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.main import MainMenu


class ScheduleMenu(CallbackData, prefix="admin_schedule_menu"):
    menu: str


def schedule_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура меню графиков для администратора.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="📤 Загрузка",
                callback_data=ScheduleMenu(menu="upload").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="📁 Локальные файлы",
                callback_data=ScheduleMenu(menu="local").pack(),
            ),
            InlineKeyboardButton(
                text="📜 История загрузок",
                callback_data=ScheduleMenu(menu="history").pack(),
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

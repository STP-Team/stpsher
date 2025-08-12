from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from tgbot.keyboards.mip.schedule.main import ScheduleMenu
from tgbot.keyboards.user.main import MainMenu


def schedule_upload_back_kb() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=ScheduleMenu(menu="list").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard

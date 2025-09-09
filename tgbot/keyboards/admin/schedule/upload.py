from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.admin.schedule.main import ScheduleMenu
from tgbot.keyboards.user.main import MainMenu


def schedule_upload_back_kb(upload_done: bool = False) -> InlineKeyboardMarkup:
    if upload_done:
        buttons = [
            [
                InlineKeyboardButton(
                    text="📤 Загрузить еще",
                    callback_data=ScheduleMenu(menu="upload").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="↩️ Назад", callback_data=MainMenu(menu="schedule").pack()
                ),
                InlineKeyboardButton(
                    text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
                ),
            ],
        ]

    else:
        buttons = [
            [
                InlineKeyboardButton(
                    text="↩️ Назад", callback_data=MainMenu(menu="schedule").pack()
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

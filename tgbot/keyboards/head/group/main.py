from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.main import MainMenu


class GroupManagementMenu(CallbackData, prefix="group_mgmt"):
    menu: str


def group_management_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура управления группой.

    :return: Объект встроенной клавиатуры для управления группой
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="📅 График",
                callback_data=GroupManagementMenu(menu="schedule").pack(),
            ),
            InlineKeyboardButton(
                text="🎖️ Рейтинг",
                callback_data=GroupManagementMenu(menu="rating").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="👥 Состав",
                callback_data=GroupManagementMenu(menu="members").pack(),
            ),
            InlineKeyboardButton(
                text="🏮 Игра",
                callback_data=GroupManagementMenu(menu="game").pack(),
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

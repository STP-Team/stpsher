from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.main import MainMenu


class GroupsCmdsMenu(CallbackData, prefix="groups_cmds"):
    menu: str


def groups_cmds_kb() -> InlineKeyboardMarkup:
    """Groups commands keyboard."""
    buttons = [
        [
            InlineKeyboardButton(
                text="🛡️ Админы",
                callback_data=GroupsCmdsMenu(menu="admins").pack(),
            ),
            InlineKeyboardButton(
                text="🙋🏻‍♂️ Пользователи",
                callback_data=GroupsCmdsMenu(menu="users").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=MainMenu(menu="groups").pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.main import MainMenu


class UserSearchMenu(CallbackData, prefix="user_search"):
    menu: str  # "specialists", "heads", "start_search"
    page: int = 1


def user_search_main_kb() -> InlineKeyboardMarkup:
    """
    Главное меню поиска для обычных пользователей (роли 1 и 3)
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="👤 Специалисты",
                callback_data=UserSearchMenu(menu="specialists").pack(),
            ),
            InlineKeyboardButton(
                text="👑 Руководители",
                callback_data=UserSearchMenu(menu="heads").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔍 Поиск по ФИО",
                callback_data=UserSearchMenu(menu="start_search").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="main").pack()
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

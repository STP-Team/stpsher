from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.main import MainMenu


class SearchMenu(CallbackData, prefix="search"):
    """Callback data для главного меню поиска"""

    menu: str
    page: int = 1
    filters: str = "НЦК,НТП1,НТП2"  # Фильтры по направлению


def search_main_kb() -> InlineKeyboardMarkup:
    """
    Главная клавиатура поиска сотрудников (для МИП)

    :return: Объект встроенной клавиатуры для поиска
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="👤 Специалисты",
                callback_data=SearchMenu(menu="specialists").pack(),
            ),
            InlineKeyboardButton(
                text="👑 Руководители", callback_data=SearchMenu(menu="heads").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="🕵🏻 Поиск",
                callback_data=SearchMenu(menu="start_search").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

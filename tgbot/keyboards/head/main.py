from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.main import MainMenu


def main_kb(group_link: str) -> InlineKeyboardMarkup:
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
                text="❤️ Моя группа",
                callback_data=MainMenu(menu="group_management").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="✍️ Активация предметов",
                callback_data=MainMenu(menu="products_activation").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔍 Поиск сотрудников",
                callback_data=MainMenu(menu="head_search").pack(),
            ),
        ],
        [
            InlineKeyboardButton(text="👋 Пригласить бота", url=group_link),
        ],
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard

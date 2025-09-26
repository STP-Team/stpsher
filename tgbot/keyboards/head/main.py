from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.main import MainMenu


def main_kb() -> InlineKeyboardMarkup:
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
                text="🕵🏻 Поиск сотрудника",
                callback_data=MainMenu(menu="search").pack(),
            ),
            InlineKeyboardButton(
                text="👯‍♀️ Группы",
                callback_data=MainMenu(menu="groups").pack(),
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard

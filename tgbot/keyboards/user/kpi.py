from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from tgbot.keyboards.user.main import MainMenu


def kpi_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура KPI.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard
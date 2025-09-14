from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from tgbot.keyboards.user.main import MainMenu


def kpi_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура для основного KPI меню.

    :return: Объект встроенной клавиатуры для KPI меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🔄 Обновить", callback_data=MainMenu(menu="kpi").pack()
            ),
            InlineKeyboardButton(
                text="🧮 Калькулятор",
                callback_data=MainMenu(menu="kpi_calculator").pack(),
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


def kpi_calculator_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура для калькулятора KPI.

    :return: Объект встроенной клавиатуры для калькулятора KPI
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🔄 Обновить", callback_data=MainMenu(menu="kpi_calculator").pack()
            ),
            InlineKeyboardButton(
                text="🌟 Показатели", callback_data=MainMenu(menu="kpi").pack()
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

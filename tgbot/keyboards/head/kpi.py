from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.main import MainMenu


class KPIMenu(CallbackData, prefix="kpi"):
    menu: str


def kpi_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура для основного KPI меню.

    :return: Объект встроенной клавиатуры для KPI меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🧮 Нормативы",
                callback_data=MainMenu(menu="kpi_calculator").pack(),
            ),
            InlineKeyboardButton(
                text="💰 Зарплата",
                callback_data=MainMenu(menu="kpi_salary").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔄 Обновить", callback_data=MainMenu(menu="kpi").pack()
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
                text="🌟 Показатели", callback_data=MainMenu(menu="kpi").pack()
            ),
            InlineKeyboardButton(
                text="💰 Зарплата",
                callback_data=MainMenu(menu="kpi_salary").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔄 Обновить", callback_data=MainMenu(menu="kpi_calculator").pack()
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


def kpi_salary_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура для расчета зарплаты.

    :return: Объект встроенной клавиатуры для расчета зарплаты
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🌟 Показатели", callback_data=MainMenu(menu="kpi").pack()
            ),
            InlineKeyboardButton(
                text="🧮 Нормативы",
                callback_data=MainMenu(menu="kpi_calculator").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔄 Обновить", callback_data=MainMenu(menu="kpi_salary").pack()
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

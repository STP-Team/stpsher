from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters.callback_data import CallbackData

from tgbot.keyboards.user.main import MainMenu


class KPIMenu(CallbackData, prefix="kpi"):
    menu: str


def kpi_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура показателей группы.

    :return: Объект встроенной клавиатуры для управления KPI группы
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data=MainMenu(menu="kpi").pack(),
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

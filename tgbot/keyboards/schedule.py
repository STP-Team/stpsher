"""Клавиатуры для графиков."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def changed_schedule_kb() -> InlineKeyboardMarkup:
    """Keyboard for schedule change notification.

    :return: InlineKeyboardMarkup with button to view schedule
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="📅 Посмотреть график", callback_data="my_schedule"
            ),
        ]
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )

    return keyboard

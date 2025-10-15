"""Клавиатуры для графиков."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def changed_schedule_kb() -> InlineKeyboardMarkup:
    """Keyboard for files_processing change notification.

    :return: InlineKeyboardMarkup with button to view files_processing
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

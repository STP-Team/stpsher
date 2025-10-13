from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def auth_kb() -> InlineKeyboardMarkup:
    """Клавиатура авторизации.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(text="🔑 Авторизация", callback_data="auth"),
        ]
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )

    return keyboard

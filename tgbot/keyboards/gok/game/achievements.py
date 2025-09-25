from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.gok.main import GokGameMenu, create_filters_row
from tgbot.keyboards.user.main import MainMenu


def gok_achievements_paginated_kb(
    page: int, total_pages: int, filters: str
) -> InlineKeyboardMarkup:
    """
    Клавиатура с пагинацией для списка достижений ГОК
    :param page: Текущая страница
    :param total_pages: Всего страниц
    :param filters: Активные фильтры
    :return:
    """
    buttons = []

    # Add filter buttons
    filter_buttons = create_filters_row("achievements_all", filters, page)
    if filter_buttons:
        buttons.append(filter_buttons)

    # Pagination controls
    nav_buttons = []

    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=GokGameMenu(
                    menu="achievements_all", page=page - 1, filters=filters
                ).pack(),
            )
        )

    nav_buttons.append(
        InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="noop",
        )
    )

    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=GokGameMenu(
                    menu="achievements_all", page=page + 1, filters=filters
                ).pack(),
            )
        )

    buttons.append(nav_buttons)

    # Back button
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)

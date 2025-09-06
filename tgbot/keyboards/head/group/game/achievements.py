from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.head.group.main import GroupManagementMenu
from tgbot.keyboards.mip.game.main import GameMenu, create_filters_row
from tgbot.keyboards.user.main import MainMenu


def head_achievements_paginated_kb(
    current_page: int, total_pages: int, filters: str = "НЦК,НТП"
) -> InlineKeyboardMarkup:
    """
    Клавиатура пагинации для всех возможных достижений с фильтрами
    """
    buttons = []

    # Пагинация
    if total_pages > 1:
        pagination_row = []

        # Первая кнопка (⏪ или пусто)
        if current_page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=GameMenu(
                        menu="achievements_all", page=1, filters=filters
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Вторая кнопка (⬅️ или пусто)
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=GameMenu(
                        menu="achievements_all", page=current_page - 1, filters=filters
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Центральная кнопка - Индикатор страницы (всегда видна)
        pagination_row.append(
            InlineKeyboardButton(
                text=f"{current_page}/{total_pages}",
                callback_data="noop",
            )
        )

        # Четвертая кнопка (➡️ или пусто)
        if current_page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=GameMenu(
                        menu="achievements_all", page=current_page + 1, filters=filters
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Пятая кнопка (⏭️ или пусто)
        if current_page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏭️",
                    callback_data=GameMenu(
                        menu="achievements_all", page=total_pages, filters=filters
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Добавляем ряд фильтров
    filter_buttons = create_filters_row("achievements_all", filters, current_page)
    buttons.append(filter_buttons)  # Все фильтры в одной строке

    # Навигация
    navigation_row = [
        InlineKeyboardButton(
            text="↩️ Назад", callback_data=GroupManagementMenu(menu="game").pack()
        ),
        InlineKeyboardButton(
            text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
        ),
    ]
    buttons.append(navigation_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

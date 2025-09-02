from typing import List

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.gok.main import (
    create_filters_row,
    GokAwardsMenu,
    GokAwardActivationMenu,
    GokLevelingMenu,
    GokAwardActionMenu,
)
from tgbot.keyboards.user.main import MainMenu


def gok_awards_paginated_kb(
    page: int, total_pages: int, filters: str
) -> InlineKeyboardMarkup:
    """
    Клавиатура с пагинацией для списка наград ГОК
    :param page: Текущая страница
    :param total_pages: Всего страниц
    :param filters: Активные фильтры
    :return:
    """
    buttons = []

    # Add filter buttons
    filter_buttons = create_filters_row("awards_all", filters, page)
    if filter_buttons:
        buttons.append(filter_buttons)

    # Pagination controls
    nav_buttons = []

    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=GokAwardsMenu(
                    menu="awards_all", page=page - 1, filters=filters
                ).pack(),
            )
        )

    nav_buttons.append(
        InlineKeyboardButton(
            text=f"📄 {page}/{total_pages}",
            callback_data="current_page",
        )
    )

    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=GokAwardsMenu(
                    menu="awards_all", page=page + 1, filters=filters
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


def gok_award_activation_kb(
    page: int, total_pages: int, page_awards: List
) -> InlineKeyboardMarkup:
    """
    Клавиатура для меню активации наград ГОК
    :param page: Текущая страница
    :param total_pages: Всего страниц
    :param page_awards: Список наград на текущей странице
    :return:
    """
    buttons = []

    # Award buttons for current page
    for i, award_detail in enumerate(page_awards):
        user_award = award_detail.award_usage
        award_info = award_detail.award_info

        # Truncate name for button display
        display_name = (
            (award_info.name[:25] + "...")
            if len(award_info.name) > 28
            else award_info.name
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{i + 1}. {display_name}",
                    callback_data=GokAwardActivationMenu(
                        user_award_id=user_award.id, page=page
                    ).pack(),
                )
            ]
        )

    # Pagination controls
    if total_pages > 1:
        nav_buttons = []

        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=GokLevelingMenu(
                        menu="awards_activation", page=page - 1
                    ).pack(),
                )
            )

        nav_buttons.append(
            InlineKeyboardButton(
                text=f"📄 {page}/{total_pages}",
                callback_data="current_page",
            )
        )

        if page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="Вперёд ➡️",
                    callback_data=GokLevelingMenu(
                        menu="awards_activation", page=page + 1
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


def gok_award_detail_kb(user_award_id: int, current_page: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для детального просмотра награды с возможностью подтверждения/отклонения
    :param user_award_id: ID награды пользователя
    :param current_page: Текущая страница в списке наград
    :return:
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=GokAwardActionMenu(
                    user_award_id=user_award_id, action="approve", page=current_page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=GokAwardActionMenu(
                    user_award_id=user_award_id, action="reject", page=current_page
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=GokLevelingMenu(
                    menu="awards_activation", page=current_page
                ).pack(),
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

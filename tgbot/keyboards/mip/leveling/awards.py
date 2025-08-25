from typing import List

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infrastructure.database.repo.user_award import UserAwardWithDetails
from tgbot.keyboards.mip.leveling.main import (
    AwardActionMenu,
    AwardActivationMenu,
    AwardsMenu,
    LevelingMenu,
    create_filters_row,
)
from tgbot.keyboards.user.main import MainMenu


def award_activation_kb(
    current_page: int, total_pages: int, page_awards: List[UserAwardWithDetails] = None
) -> InlineKeyboardMarkup:
    """
    Клавиатура для списка наград ожидающих активации
    """
    buttons = []

    # Добавляем кнопки для выбора наград (максимум 2 в ряд)
    if page_awards:
        # Вычисляем стартовый индекс для нумерации на текущей странице
        start_idx = (current_page - 1) * 5  # 5 наград на страницу

        for i in range(0, len(page_awards), 2):
            award_row = []

            # Первая награда в ряду
            first_award = page_awards[i]
            first_award_number = start_idx + i + 1
            award_row.append(
                InlineKeyboardButton(
                    text=f"{first_award_number}. {first_award.award_info.name}",
                    callback_data=AwardActivationMenu(
                        user_award_id=first_award.user_award.id, page=current_page
                    ).pack(),
                )
            )

            # Вторая награда в ряду (если есть)
            if i + 1 < len(page_awards):
                second_award = page_awards[i + 1]
                second_award_number = start_idx + i + 2
                award_row.append(
                    InlineKeyboardButton(
                        text=f"{second_award_number}. {second_award.award_info.name}",
                        callback_data=AwardActivationMenu(
                            user_award_id=second_award.user_award.id, page=current_page
                        ).pack(),
                    )
                )

            buttons.append(award_row)

    # Пагинация
    if total_pages > 1:
        pagination_row = []

        # Первая кнопка (⏪ или пусто)
        if current_page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=LevelingMenu(menu="awards_activation", page=1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Вторая кнопка (⬅️ или пусто)
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=LevelingMenu(
                        menu="awards_activation", page=current_page - 1
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Центральная кнопка - Индикатор страницы
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
                    callback_data=LevelingMenu(
                        menu="awards_activation", page=current_page + 1
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
                    callback_data=LevelingMenu(
                        menu="awards_activation", page=total_pages
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Навигация
    navigation_row = [
        InlineKeyboardButton(
            text="↩️ Назад", callback_data=MainMenu(menu="leveling").pack()
        ),
        InlineKeyboardButton(
            text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
        ),
    ]
    buttons.append(navigation_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def award_detail_kb(user_award_id: int, current_page: int) -> InlineKeyboardMarkup:
    """
    Клавиатура детального просмотра награды для МИП с возможностью подтверждения/отклонения
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=AwardActionMenu(
                    user_award_id=user_award_id, action="approve", page=current_page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=AwardActionMenu(
                    user_award_id=user_award_id, action="reject", page=current_page
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=LevelingMenu(
                    menu="awards_activation", page=current_page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def awards_paginated_kb(
    current_page: int, total_pages: int, filters: str = "НЦК,НТП"
) -> InlineKeyboardMarkup:
    """
    Клавиатура пагинации для всех возможных наград с фильтрами
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
                    callback_data=AwardsMenu(
                        menu="awards_all", page=1, filters=filters
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
                    callback_data=AwardsMenu(
                        menu="awards_all", page=current_page - 1, filters=filters
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
                    callback_data=AwardsMenu(
                        menu="awards_all", page=current_page + 1, filters=filters
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
                    callback_data=AwardsMenu(
                        menu="awards_all", page=total_pages, filters=filters
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Добавляем ряд фильтров
    filter_buttons = create_filters_row("awards_all", filters, current_page)
    buttons.append(filter_buttons)  # Все фильтры в одной строке

    # Навигация
    navigation_row = [
        InlineKeyboardButton(
            text="↩️ Назад", callback_data=MainMenu(menu="leveling").pack()
        ),
        InlineKeyboardButton(
            text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
        ),
    ]
    buttons.append(navigation_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

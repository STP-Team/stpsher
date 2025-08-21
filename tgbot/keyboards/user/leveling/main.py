from typing import List

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infrastructure.database.repo.user_award import UserAwardWithDetails
from tgbot.keyboards.mip.leveling.main import LevelingMenu
from tgbot.keyboards.user.main import MainMenu


class AchievementsMenu(CallbackData, prefix="achievements"):
    menu: str


class AwardsMenu(CallbackData, prefix="awards"):
    menu: str
    page: int = 1
    award_id: int = 0


class AwardDetailMenu(CallbackData, prefix="award_detail"):
    user_award_id: int


def get_status_emoji(status: str) -> str:
    """Возвращает эмодзи в зависимости от статуса"""
    status_emojis = {
        "waiting": "⏳",
        "approved": "✅",
        "canceled": "🔥",
        "rejected": "⛔",
    }
    return status_emojis.get(status, "❓")


def leveling_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура меню достижений.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🎯 Достижения",
                callback_data=LevelingMenu(menu="achievements").pack(),
            ),
            InlineKeyboardButton(
                text="👏 Награды",
                callback_data=LevelingMenu(menu="awards").pack(),
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


def achievements_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура меню достижений.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🔎 Детализация",
                callback_data=AchievementsMenu(menu="details").pack(),
            ),
            InlineKeyboardButton(
                text="🏆 Все возможные",
                callback_data=AchievementsMenu(menu="all").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="leveling").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard


def awards_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура меню наград.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="❇️ Доступные", callback_data=AwardsMenu(menu="available").pack()
            ),
            InlineKeyboardButton(
                text="✴️ Использованные",
                callback_data=AwardsMenu(menu="executed").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🏆 Все возможные", callback_data=AwardsMenu(menu="all").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="leveling").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard


def awards_paginated_kb(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []

    # Пагинация
    if total_pages > 1:
        pagination_row = []

        # Клавиатура
        # [⏪] [⬅️] [страница] [➡️] [⏭️]

        # Первая кнопка (⏪ или пусто)
        if current_page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=AwardsMenu(menu="all", page=1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Вторая кнопка (⬅️ или пусто)
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=AwardsMenu(menu="all", page=current_page - 1).pack(),
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
                    callback_data=AwardsMenu(menu="all", page=current_page + 1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Пятая кнопка (⏭️ или пусто)
        if current_page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏭️",
                    callback_data=AwardsMenu(menu="all", page=total_pages).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Навигация
    navigation_row = [
        InlineKeyboardButton(
            text="↩️ Назад", callback_data=LevelingMenu(menu="awards").pack()
        ),
        InlineKeyboardButton(
            text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
        ),
    ]
    buttons.append(navigation_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def award_history_kb(user_awards: List[UserAwardWithDetails]) -> InlineKeyboardMarkup:
    """
    Клавиатура истории наград пользователя.
    Каждая кнопка содержит название награды, дату и эмодзи статуса.
    """
    buttons = []

    for award_detail in user_awards:
        user_award = award_detail.user_award
        award_info = award_detail.award_info

        # Форматируем дату в формате DD.MM.YY
        date_str = user_award.bought_at.strftime("%d.%m.%y")

        # Получаем эмодзи статуса
        status_emoji = get_status_emoji(user_award.status)

        # Формируем текст кнопки
        button_text = f"{status_emoji} {award_info.name} ({date_str})"

        buttons.append(
            [
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=AwardDetailMenu(user_award_id=user_award.id).pack(),
                )
            ]
        )

    # Добавляем кнопки навигации
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=LevelingMenu(menu="awards").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def award_detail_back_kb() -> InlineKeyboardMarkup:
    """Клавиатура для возврата из детального просмотра награды"""
    buttons = [
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=AwardsMenu(menu="executed").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

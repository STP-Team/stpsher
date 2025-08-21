from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.mip.leveling.main import LevelingMenu
from tgbot.keyboards.user.main import MainMenu


class AchievementsMenu(CallbackData, prefix="achievements"):
    menu: str


class AwardsMenu(CallbackData, prefix="awards"):
    menu: str
    page: int = 1
    award_id: int = 0


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

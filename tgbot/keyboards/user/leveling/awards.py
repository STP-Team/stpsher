from typing import List

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infrastructure.database.models import User
from infrastructure.database.repo.STP.award_usage import AwardUsageWithDetails
from tgbot.keyboards.mip.leveling.main import LevelingMenu
from tgbot.keyboards.user.main import MainMenu


class UseAwardMenu(CallbackData, prefix="use_award"):
    user_award_id: int


class AwardHistoryMenu(CallbackData, prefix="award_history"):
    menu: str = "history"
    page: int = 1


class AwardPurchaseMenu(CallbackData, prefix="award_purchase"):
    award_id: int
    page: int = 1


class AwardPurchaseConfirmMenu(CallbackData, prefix="award_buy_confirm"):
    award_id: int
    page: int = 1
    action: str  # "buy" or "back"


class AwardsMenu(CallbackData, prefix="awards"):
    menu: str
    page: int = 1
    award_id: int = 0


class AwardDetailMenu(CallbackData, prefix="award_detail"):
    user_award_id: int


class SellAwardMenu(CallbackData, prefix="sell_award"):
    user_award_id: int
    source_menu: str = "bought"  # "bought" или "available"


class CancelActivationMenu(CallbackData, prefix="cancel_activation"):
    user_award_id: int


class DutyAwardActivationMenu(CallbackData, prefix="duty_activation"):
    user_award_id: int
    page: int = 1


class DutyAwardActionMenu(CallbackData, prefix="duty_action"):
    user_award_id: int
    action: str  # "approve" or "reject"
    page: int = 1


class DutyActivationListMenu(CallbackData, prefix="duty_list"):
    menu: str = "duty_activation"
    page: int = 1


def get_status_emoji(status: str) -> str:
    status_emojis = {
        "stored": "📦",
        "review": "⏳",
        "used_up": "🔒",
        "canceled": "❌",
        "rejected": "⛔",
    }
    return status_emojis.get(status, "❓")


def awards_kb(user: User = None) -> InlineKeyboardMarkup:
    """
    Клавиатура меню наград.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = []

    # Add duty activation button first if user is a duty (role 3)
    if user and user.role == 3:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✍️ Активация наград",
                    callback_data=LevelingMenu(menu="awards_activation").pack(),
                ),
            ]
        )

    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="❇️ Доступные",
                    callback_data=AwardsMenu(menu="available").pack(),
                ),
                InlineKeyboardButton(
                    text="✴️ Купленные",
                    callback_data=AwardsMenu(menu="executed").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏆 Все возможные", callback_data=AwardsMenu(menu="all").pack()
                ),
            ],
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard


def available_awards_paginated_kb(
    current_page: int, total_pages: int, page_awards: list = None
) -> InlineKeyboardMarkup:
    """
    Клавиатура пагинации для доступных наград с кнопками выбора наград
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
                    text=f"{first_award_number}. {first_award.name}",
                    callback_data=AwardPurchaseMenu(
                        award_id=first_award.id, page=current_page
                    ).pack(),
                )
            )

            # Вторая награда в ряду (если есть)
            if i + 1 < len(page_awards):
                second_award = page_awards[i + 1]
                second_award_number = start_idx + i + 2
                award_row.append(
                    InlineKeyboardButton(
                        text=f"{second_award_number}. {second_award.name}",
                        callback_data=AwardPurchaseMenu(
                            award_id=second_award.id, page=current_page
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
                    callback_data=AwardsMenu(menu="available", page=1).pack(),
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
                        menu="available", page=current_page - 1
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
                        menu="available", page=current_page + 1
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
                    callback_data=AwardsMenu(menu="available", page=total_pages).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Навигация
    navigation_row = [
        InlineKeyboardButton(
            text="↩️ Назад", callback_data=MainMenu(menu="awards").pack()
        ),
        InlineKeyboardButton(
            text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
        ),
    ]
    buttons.append(navigation_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def award_confirmation_kb(award_id: int, page: int) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения покупки награды
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Купить награду",
                callback_data=AwardPurchaseConfirmMenu(
                    award_id=award_id, page=page, action="buy"
                ).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=AwardPurchaseConfirmMenu(
                    award_id=award_id, page=page, action="back"
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def duty_award_activation_kb(
    current_page: int, total_pages: int, page_awards: list = None
) -> InlineKeyboardMarkup:
    """
    Клавиатура пагинации для активации наград дежурными
    """
    buttons = []

    # Добавляем кнопки для выбора наград (по одной в ряд из-за длинных названий)
    if page_awards:
        start_idx = (current_page - 1) * 5  # 5 наград на страницу

        for i, award_detail in enumerate(page_awards):
            user_award = award_detail.user_award
            award_info = award_detail.award_info
            award_number = start_idx + i + 1

            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{award_number}. {award_info.name}",
                        callback_data=DutyAwardActivationMenu(
                            user_award_id=user_award.id, page=current_page
                        ).pack(),
                    )
                ]
            )

    # Пагинация
    if total_pages > 1:
        pagination_row = []

        # Первая кнопка (⏪ или пусто)
        if current_page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=DutyActivationListMenu(
                        menu="duty_activation", page=1
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
                    callback_data=DutyActivationListMenu(
                        menu="duty_activation", page=current_page - 1
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
                    callback_data=DutyActivationListMenu(
                        menu="duty_activation", page=current_page + 1
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
                    callback_data=DutyActivationListMenu(
                        menu="duty_activation", page=total_pages
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Навигация
    navigation_row = [
        InlineKeyboardButton(
            text="↩️ Назад", callback_data=MainMenu(menu="awards").pack()
        ),
        InlineKeyboardButton(
            text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
        ),
    ]
    buttons.append(navigation_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def duty_award_detail_kb(user_award_id: int, current_page: int) -> InlineKeyboardMarkup:
    """Клавиатура для детального просмотра награды дежурным"""
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=DutyAwardActionMenu(
                    user_award_id=user_award_id, action="approve", page=current_page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=DutyAwardActionMenu(
                    user_award_id=user_award_id, action="reject", page=current_page
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=DutyActivationListMenu(
                    menu="duty_activation", page=current_page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
            text="↩️ Назад", callback_data=MainMenu(menu="awards").pack()
        ),
        InlineKeyboardButton(
            text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
        ),
    ]
    buttons.append(navigation_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def award_history_kb(
    user_awards: List[AwardUsageWithDetails],
    current_page: int = 1,
    awards_per_page: int = 8,
) -> InlineKeyboardMarkup:
    """
    Клавиатура истории наград пользователя с пагинацией.
    Отображает 2 награды в ряд, по умолчанию 8 наград на страницу (4 ряда).
    """
    buttons = []

    # Рассчитываем пагинацию
    total_awards = len(user_awards)
    total_pages = (total_awards + awards_per_page - 1) // awards_per_page

    # Рассчитываем диапазон наград для текущей страницы
    start_idx = (current_page - 1) * awards_per_page
    end_idx = start_idx + awards_per_page
    page_awards = user_awards[start_idx:end_idx]

    # Создаем кнопки для наград (2 в ряд)
    for i in range(0, len(page_awards), 2):
        row = []

        # Первая награда в ряду
        award_detail = page_awards[i]
        user_award = award_detail.user_award
        award_info = award_detail.award_info

        date_str = user_award.bought_at.strftime("%d.%m.%y")
        status_emoji = get_status_emoji(user_award.status)
        usage_info = f"({award_detail.current_usages}/{award_detail.max_usages})"
        button_text = f"{status_emoji} {usage_info} {award_info.name} ({date_str})"

        row.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=AwardDetailMenu(user_award_id=user_award.id).pack(),
            )
        )

        # Вторая награда в ряду (если есть)
        if i + 1 < len(page_awards):
            award_detail = page_awards[i + 1]
            user_award = award_detail.user_award
            award_info = award_detail.award_info

            date_str = user_award.bought_at.strftime("%d.%m.%y")
            status_emoji = get_status_emoji(user_award.status)
            usage_info = f"({award_detail.current_usages}/{award_detail.max_usages})"
            button_text = f"{status_emoji} {usage_info} {award_info.name} ({date_str})"

            row.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=AwardDetailMenu(user_award_id=user_award.id).pack(),
                )
            )

        buttons.append(row)

    # Добавляем пагинацию (только если больше одной страницы)
    if total_pages > 1:
        pagination_row = []

        # Клавиатура пагинации: [⏪] [⬅️] [страница] [➡️] [⏭️]

        # Первая кнопка (⏪ или пусто)
        if current_page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=AwardHistoryMenu(menu="history", page=1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Вторая кнопка (⬅️ или пусто)
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=AwardHistoryMenu(
                        menu="history", page=current_page - 1
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
                    callback_data=AwardHistoryMenu(
                        menu="history", page=current_page + 1
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
                    callback_data=AwardHistoryMenu(
                        menu="history", page=total_pages
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Добавляем кнопки навигации
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="awards").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def to_awards_kb() -> InlineKeyboardMarkup:
    """Клавиатура для возврата из детального просмотра награды"""
    buttons = [
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="awards").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    ]

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


def award_detail_kb(
    user_award_id: int,
    can_use: bool = False,
    can_sell: bool = False,
    can_cancel: bool = False,
    source_menu: str = "bought",
) -> InlineKeyboardMarkup:
    buttons = []

    if can_use:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🎯 Использовать награду",
                    callback_data=UseAwardMenu(user_award_id=user_award_id).pack(),
                )
            ]
        )

    if can_sell:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="💸 Вернуть",
                    callback_data=SellAwardMenu(
                        user_award_id=user_award_id, source_menu=source_menu
                    ).pack(),
                )
            ]
        )

    if can_cancel:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✋🏻 Отменить активацию",
                    callback_data=CancelActivationMenu(
                        user_award_id=user_award_id
                    ).pack(),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=AwardsMenu(menu="executed").pack()
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def award_purchase_success_kb(user_award_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для успешной покупки награды
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🎯 Использовать награду",
                callback_data=UseAwardMenu(user_award_id=user_award_id).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="💸 Вернуть",
                callback_data=SellAwardMenu(
                    user_award_id=user_award_id,
                    source_menu="available",
                ).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="❇️ К доступным",
                callback_data=AwardsMenu(menu="available").pack(),
            ),
            InlineKeyboardButton(
                text="✴️ К купленным",
                callback_data=AwardsMenu(menu="executed").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

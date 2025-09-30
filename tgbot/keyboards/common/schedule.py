from datetime import datetime, timedelta

import pytz
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.main import MainMenu

# Список месяцев на русском языке
MONTHS_RU = [
    "январь",
    "февраль",
    "март",
    "апрель",
    "май",
    "июнь",
    "июль",
    "август",
    "сентябрь",
    "октябрь",
    "ноябрь",
    "декабрь",
]

# Эмодзи для месяцев
MONTH_EMOJIS = {
    "январь": "❄️",
    "февраль": "💙",
    "март": "🌸",
    "апрель": "🌷",
    "май": "🌻",
    "июнь": "☀️",
    "июль": "🏖️",
    "август": "🌾",
    "сентябрь": "🍂",
    "октябрь": "🎃",
    "ноябрь": "🍁",
    "декабрь": "🎄",
}


class ScheduleMenu(CallbackData, prefix="schedule_menu"):
    menu: str


class HeadNavigation(CallbackData, prefix="head_nav"):
    """Callback data для навигации по дням для руководителей групп"""

    action: str  # "prev", "next", "-", "today"
    date: str  # дата в формате YYYY-MM-DD


class DutyNavigation(CallbackData, prefix="duty_nav"):
    """Callback data для навигации по дням дежурств"""

    action: str  # "prev", "next", "-", "today"
    date: str  # дата в формате YYYY-MM-DD


class GroupNavigation(CallbackData, prefix="group_nav"):
    """Callback data для навигации по групповому расписанию"""

    action: str  # "prev", "next", "prev_page", "next_page", "-", "today"
    date: str  # дата в формате YYYY-MM-DD
    page: int = 1  # номер страницы для пагинации
    user_type: str = "user"  # "head" или "user"
    from_group_mgmt: bool = False  # вызвано ли из меню управления группой


class MonthNavigation(CallbackData, prefix="month_nav"):
    action: str  # "prev", "next", "current"
    month: str


def get_yekaterinburg_date() -> datetime:
    """Получает текущую дату по Екатеринбургу"""
    yekaterinburg_tz = pytz.timezone("Asia/Yekaterinburg")
    return datetime.now(yekaterinburg_tz)


def get_next_month(current_month: str) -> str:
    """
    Получает следующий месяц (логически следующий, не зависит от доступности в файлах)

    Args:
        current_month: Текущий месяц

    Returns:
        Следующий месяц
    """
    try:
        current_index = MONTHS_RU.index(current_month.lower())
        if current_index < len(MONTHS_RU) - 1:
            return MONTHS_RU[current_index + 1]
        else:
            return MONTHS_RU[0]  # Январь после декабря
    except (ValueError, IndexError):
        # Если месяц не найден, возвращаем следующий от текущего календарного месяца
        current_month_index = get_yekaterinburg_date().month - 1
        next_month_index = (current_month_index + 1) % 12
        return MONTHS_RU[next_month_index]


def get_prev_month(current_month: str) -> str:
    """
    Получает предыдущий месяц (логически предыдущий, не зависит от доступности в файлах)

    Args:
        current_month: Текущий месяц

    Returns:
        Предыдущий месяц
    """
    try:
        current_index = MONTHS_RU.index(current_month.lower())
        if current_index > 0:
            return MONTHS_RU[current_index - 1]
        else:
            return MONTHS_RU[-1]  # Декабрь перед январем
    except (ValueError, IndexError):
        # Если месяц не найден, возвращаем предыдущий от текущего календарного месяца
        current_month_index = get_yekaterinburg_date().month - 1
        prev_month_index = (current_month_index - 1) % 12
        return MONTHS_RU[prev_month_index]


def duties_kb(current_date: datetime = None) -> InlineKeyboardMarkup:
    """
    Клавиатура для навигации по дежурствам

    Args:
        current_date: Текущая отображаемая дата

    Returns:
        Клавиатура с навигацией по дням
    """
    if current_date is None:
        current_date = get_yekaterinburg_date()

    # Получаем даты для навигации
    prev_date = current_date - timedelta(days=1)
    next_date = current_date + timedelta(days=1)
    today = get_yekaterinburg_date().date()

    # Форматируем дату для отображения
    date_str = current_date.strftime("%d.%m")

    # Создаем ряд навигации по дням
    nav_row = [
        InlineKeyboardButton(
            text="⬅️",
            callback_data=DutyNavigation(
                action="prev", date=prev_date.strftime("%Y-%m-%d")
            ).pack(),
        ),
        InlineKeyboardButton(
            text=f"📅 {date_str}",
            callback_data=DutyNavigation(
                action="-", date=current_date.strftime("%Y-%m-%d")
            ).pack(),
        ),
        InlineKeyboardButton(
            text="➡️",
            callback_data=DutyNavigation(
                action="next", date=next_date.strftime("%Y-%m-%d")
            ).pack(),
        ),
    ]

    buttons = [nav_row]

    # Добавляем кнопку "Сегодня" только если отображается не сегодняшний день
    if current_date.date() != today:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📍 Сегодня",
                    callback_data=DutyNavigation(
                        action="today", date=today.strftime("%Y-%m-%d")
                    ).pack(),
                )
            ]
        )

    # Кнопка возврата
    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=ScheduleMenu(menu="main").pack(),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def heads_kb(current_date: datetime = None) -> InlineKeyboardMarkup:
    """
    Клавиатура для навигации по руководителям

    Args:
        current_date: Текущая отображаемая дата

    Returns:
        Клавиатура с навигацией по дням
    """
    if current_date is None:
        current_date = get_yekaterinburg_date()

    # Получаем даты для навигации
    prev_date = current_date - timedelta(days=1)
    next_date = current_date + timedelta(days=1)
    today = get_yekaterinburg_date().date()

    # Форматируем дату для отображения
    date_str = current_date.strftime("%d.%m")

    # Создаем ряд навигации по дням
    nav_row = [
        InlineKeyboardButton(
            text="⬅️",
            callback_data=HeadNavigation(
                action="prev", date=prev_date.strftime("%Y-%m-%d")
            ).pack(),
        ),
        InlineKeyboardButton(
            text=f"📅 {date_str}",
            callback_data=HeadNavigation(
                action="-", date=current_date.strftime("%Y-%m-%d")
            ).pack(),
        ),
        InlineKeyboardButton(
            text="➡️",
            callback_data=HeadNavigation(
                action="next", date=next_date.strftime("%Y-%m-%d")
            ).pack(),
        ),
    ]

    buttons = [nav_row]

    # Добавляем кнопку "Сегодня" только если отображается не сегодняшний день
    if current_date.date() != today:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📍 Сегодня",
                    callback_data=HeadNavigation(
                        action="today", date=today.strftime("%Y-%m-%d")
                    ).pack(),
                )
            ]
        )

    # Кнопка возврата
    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=ScheduleMenu(menu="main").pack(),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def group_schedule_kb(
    current_date: datetime = None,
    total_pages: int = 1,
    current_page: int = 1,
    user_type: str = "user",
    from_group_mgmt: bool = False,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для группового расписания с пагинацией и навигацией по дням

    Args:
        current_date: Текущая отображаемая дата
        total_pages: Общее количество страниц
        current_page: Текущая страница
        user_type: Тип пользователя ("head" или "user")
        from_group_mgmt: Вызвано ли из меню управления группой

    Returns:
        Клавиатура с навигацией
    """
    if current_date is None:
        current_date = get_yekaterinburg_date()

    buttons = []

    # Ряд навигации по дням
    if not from_group_mgmt:
        prev_date = current_date - timedelta(days=1)
        next_date = current_date + timedelta(days=1)
        today = get_yekaterinburg_date().date()
        date_str = current_date.strftime("%d.%m")

        nav_row = [
            InlineKeyboardButton(
                text="⬅️",
                callback_data=GroupNavigation(
                    action="prev",
                    date=prev_date.strftime("%Y-%m-%d"),
                    page=current_page,
                    user_type=user_type,
                    from_group_mgmt=from_group_mgmt,
                ).pack(),
            ),
            InlineKeyboardButton(
                text=f"📅 {date_str}",
                callback_data=GroupNavigation(
                    action="-",
                    date=current_date.strftime("%Y-%m-%d"),
                    page=current_page,
                    user_type=user_type,
                    from_group_mgmt=from_group_mgmt,
                ).pack(),
            ),
            InlineKeyboardButton(
                text="➡️",
                callback_data=GroupNavigation(
                    action="next",
                    date=next_date.strftime("%Y-%m-%d"),
                    page=current_page,
                    user_type=user_type,
                    from_group_mgmt=from_group_mgmt,
                ).pack(),
            ),
        ]
        buttons.append(nav_row)

        # Кнопка "Сегодня" если не сегодня
        if current_date.date() != today:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="📍 Сегодня",
                        callback_data=GroupNavigation(
                            action="today",
                            date=today.strftime("%Y-%m-%d"),
                            page=1,
                            user_type=user_type,
                            from_group_mgmt=from_group_mgmt,
                        ).pack(),
                    )
                ]
            )

    # Ряд пагинации (только если больше одной страницы)
    if total_pages > 1:
        pagination_row = []

        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️ Пред",
                    callback_data=GroupNavigation(
                        action="prev_page",
                        date=current_date.strftime("%Y-%m-%d"),
                        page=current_page - 1,
                        user_type=user_type,
                        from_group_mgmt=from_group_mgmt,
                    ).pack(),
                )
            )

        pagination_row.append(
            InlineKeyboardButton(
                text=f"{current_page}/{total_pages}",
                callback_data=GroupNavigation(
                    action="-",
                    date=current_date.strftime("%Y-%m-%d"),
                    page=current_page,
                    user_type=user_type,
                    from_group_mgmt=from_group_mgmt,
                ).pack(),
            )
        )

        if current_page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(
                    text="След ➡️",
                    callback_data=GroupNavigation(
                        action="next_page",
                        date=current_date.strftime("%Y-%m-%d"),
                        page=current_page + 1,
                        user_type=user_type,
                        from_group_mgmt=from_group_mgmt,
                    ).pack(),
                )
            )

        buttons.append(pagination_row)

    # Кнопка возврата
    if from_group_mgmt:
        from tgbot.keyboards.head.group.main import GroupManagementMenu

        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=GroupManagementMenu(menu="main").pack(),
                )
            ]
        )
    else:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=ScheduleMenu(menu="main").pack(),
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def schedule_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура главного меню графиков

    Returns:
        Клавиатура с основными разделами графиков
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="📅 Мой график",
                callback_data=ScheduleMenu(menu="my").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="👮 Дежурные",
                callback_data=ScheduleMenu(menu="duties").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 Группа",
                callback_data=ScheduleMenu(menu="group").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Главное меню",
                callback_data=MainMenu(menu="main").pack(),
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def schedule_with_month_kb(current_month: str = None) -> InlineKeyboardMarkup:
    """
    Клавиатура для расписания с навигацией по месяцам

    Args:
        current_month: Текущий месяц

    Returns:
        Клавиатура с навигацией по месяцам
    """
    buttons = []

    # Навигация по месяцам
    month_row = []

    if current_month:
        try:
            current_idx = MONTHS_RU.index(current_month.lower())
            prev_idx = (current_idx - 1) % 12
            next_idx = (current_idx + 1) % 12

            prev_month = MONTHS_RU[prev_idx]
            next_month = MONTHS_RU[next_idx]

            month_row = [
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=MonthNavigation(
                        action="prev", month=prev_month
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text=f"{MONTH_EMOJIS.get(current_month.lower(), '📅')} {current_month.capitalize()}",
                    callback_data=MonthNavigation(
                        action="current", month=current_month
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=MonthNavigation(
                        action="next", month=next_month
                    ).pack(),
                ),
            ]
        except ValueError:
            # Если месяц не найден, показываем текущий
            current_month_idx = get_yekaterinburg_date().month - 1
            current_month = MONTHS_RU[current_month_idx]
            month_row = [
                InlineKeyboardButton(
                    text=f"{MONTH_EMOJIS.get(current_month, '📅')} {current_month.capitalize()}",
                    callback_data=MonthNavigation(
                        action="current", month=current_month
                    ).pack(),
                ),
            ]
    else:
        current_month_idx = get_yekaterinburg_date().month - 1
        current_month = MONTHS_RU[current_month_idx]
        month_row = [
            InlineKeyboardButton(
                text=f"{MONTH_EMOJIS.get(current_month, '📅')} {current_month.capitalize()}",
                callback_data=MonthNavigation(
                    action="current", month=current_month
                ).pack(),
            ),
        ]

    buttons.append(month_row)

    # Кнопки действий
    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="📋 Подробно",
                    callback_data=ScheduleMenu(menu="detailed").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=ScheduleMenu(menu="main").pack(),
                )
            ],
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_detailed_schedule_keyboard(
    current_month: str = None,
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для детального просмотра расписания

    Args:
        current_month: Текущий месяц

    Returns:
        Клавиатура для детального просмотра
    """
    buttons = []

    # Навигация по месяцам (как в schedule_with_month_kb)
    month_row = []

    if current_month:
        try:
            current_idx = MONTHS_RU.index(current_month.lower())
            prev_idx = (current_idx - 1) % 12
            next_idx = (current_idx + 1) % 12

            prev_month = MONTHS_RU[prev_idx]
            next_month = MONTHS_RU[next_idx]

            month_row = [
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=MonthNavigation(
                        action="prev", month=prev_month
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text=f"{MONTH_EMOJIS.get(current_month.lower(), '📅')} {current_month.capitalize()}",
                    callback_data=MonthNavigation(
                        action="current", month=current_month
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=MonthNavigation(
                        action="next", month=next_month
                    ).pack(),
                ),
            ]
        except ValueError:
            # Если месяц не найден, показываем текущий
            current_month_idx = get_yekaterinburg_date().month - 1
            current_month = MONTHS_RU[current_month_idx]
            month_row = [
                InlineKeyboardButton(
                    text=f"{MONTH_EMOJIS.get(current_month, '📅')} {current_month.capitalize()}",
                    callback_data=MonthNavigation(
                        action="current", month=current_month
                    ).pack(),
                ),
            ]

    buttons.append(month_row)

    # Кнопки действий
    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="📝 Кратко",
                    callback_data=ScheduleMenu(menu="my").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=ScheduleMenu(menu="main").pack(),
                )
            ],
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def changed_schedule_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура для отправки специалисту при изменении графика

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="👔 Мой график", callback_data=ScheduleMenu(menu="my").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard

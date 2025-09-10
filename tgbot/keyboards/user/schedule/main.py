from datetime import datetime, timedelta
from typing import List

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


def get_yekaterinburg_date() -> datetime:
    """Получает текущую дату по Екатеринбургу"""
    yekaterinburg_tz = pytz.timezone("Asia/Yekaterinburg")
    return datetime.now(yekaterinburg_tz)


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
            text="◀️",
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
            text="▶️",
            callback_data=DutyNavigation(
                action="next", date=next_date.strftime("%Y-%m-%d")
            ).pack(),
        ),
    ]

    buttons = [nav_row]

    # Добавляем кнопку "Сегодня" если смотрим не сегодняшний день
    if current_date.date() != today:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📍 Сегодня",
                    callback_data=DutyNavigation(
                        action="today", date=today.strftime("%Y-%m-%d")
                    ).pack(),
                ),
            ]
        )

    # Кнопки навигации
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="schedule").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


class MonthNavigation(CallbackData, prefix="month_nav"):
    """Callback data для навигации по месяцам"""

    action: str  # "prev", "next", "-", "detailed", "compact"
    current_month: str  # текущий месяц
    schedule_type: str = "my"  # "my", "duties", "heads"


def schedule_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура меню графиков.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="👔 Мой график", callback_data=ScheduleMenu(menu="my").pack()
            ),
            InlineKeyboardButton(
                text="❤️ Моя группа", callback_data=ScheduleMenu(menu="group").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="👮‍♂️ Дежурные", callback_data=ScheduleMenu(menu="duties").pack()
            ),
            InlineKeyboardButton(
                text="👑 Руководители", callback_data=ScheduleMenu(menu="heads").pack()
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


def get_available_months() -> List[str]:
    """
    Получает список доступных месяцев из Excel файла

    Returns:
        Список доступных месяцев
    """
    # TODO: Здесь можно добавить логику для автоматического определения
    # доступных месяцев из Excel файла
    # Пока возвращаем все месяцы
    return MONTHS_RU


def get_month_index(month: str) -> int:
    """
    Получает индекс месяца в списке

    Args:
        month: Название месяца

    Returns:
        Индекс месяца или 0, если не найден
    """
    try:
        return MONTHS_RU.index(month.lower())
    except ValueError:
        return 0


def get_next_month(current_month: str, available_months: List[str]) -> str:
    """
    Получает следующий доступный месяц

    Args:
        current_month: Текущий месяц
        available_months: Список доступных месяцев

    Returns:
        Следующий месяц или текущий, если следующего нет
    """
    try:
        current_index = available_months.index(current_month.lower())
        if current_index < len(available_months) - 1:
            return available_months[current_index + 1]
        else:
            return current_month.lower()  # Возвращаем текущий, если следующего нет
    except (ValueError, IndexError):
        return current_month.lower()


def get_prev_month(current_month: str, available_months: List[str]) -> str:
    """
    Получает предыдущий доступный месяц

    Args:
        current_month: Текущий месяц
        available_months: Список доступных месяцев

    Returns:
        Предыдущий месяц или текущий, если предыдущего нет
    """
    try:
        current_index = available_months.index(current_month.lower())
        if current_index > 0:
            return available_months[current_index - 1]
        else:
            return current_month.lower()  # Возвращаем текущий, если предыдущего нет
    except (ValueError, IndexError):
        return current_month.lower()


def schedule_with_month_kb(
    current_month: str, schedule_type: str = "my"
) -> InlineKeyboardMarkup:
    """
    Объединенная клавиатура: меню расписаний + навигация по месяцам

    Args:
        current_month: Текущий выбранный месяц
        schedule_type: Тип пользователя

    Returns:
        Объект встроенной клавиатуры
    """
    available_months = get_available_months()
    current_month = current_month.lower()

    # Получаем предыдущий и следующий месяцы
    prev_month = get_prev_month(current_month, available_months)
    next_month = get_next_month(current_month, available_months)

    # Эмодзи для текущего месяца
    month_emoji = MONTH_EMOJIS.get(current_month, "📅")

    # Создаем ряд навигации по месяцам
    nav_row = []

    # Кнопка "Назад" (только если есть предыдущий месяц)
    if prev_month != current_month:
        nav_row.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=MonthNavigation(
                    action="prev", current_month=prev_month, schedule_type=schedule_type
                ).pack(),
            )
        )

    # Кнопка текущего месяца (всегда присутствует)
    nav_row.append(
        InlineKeyboardButton(
            text=f"{month_emoji} {current_month.capitalize()}",
            callback_data=MonthNavigation(
                action="-",
                current_month=current_month,
                schedule_type=schedule_type,
            ).pack(),
        )
    )

    # Кнопка "Вперед" (только если есть следующий месяц)
    if next_month != current_month:
        nav_row.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=MonthNavigation(
                    action="next", current_month=next_month, schedule_type=schedule_type
                ).pack(),
            )
        )

    buttons = [
        nav_row,  # Ряд навигации по месяцам
        [
            InlineKeyboardButton(
                text="📋 Подробнее",
                callback_data=MonthNavigation(
                    action="detailed",
                    current_month=current_month,
                    schedule_type=schedule_type,
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="schedule").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def create_detailed_schedule_keyboard(current_month: str, schedule_type: str):
    """Создает клавиатуру для детального режима расписания"""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    available_months = get_available_months()
    current_month_lower = current_month.lower()

    # Получаем предыдущий и следующий месяцы
    prev_month = get_prev_month(current_month_lower, available_months)
    next_month = get_next_month(current_month_lower, available_months)

    # Эмодзи для текущего месяца
    month_emoji = MONTH_EMOJIS.get(current_month_lower, "📅")

    buttons = []

    # Навигация по месяцам (только если есть доступные месяцы)
    nav_row = []

    # Кнопка "Назад" (только если есть предыдущий месяц)
    if prev_month != current_month_lower:  # Есть предыдущий месяц
        nav_row.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=MonthNavigation(
                    action="prev", current_month=prev_month, schedule_type=schedule_type
                ).pack(),
            )
        )

    # Текущий месяц
    nav_row.append(
        InlineKeyboardButton(
            text=f"{month_emoji} {current_month.capitalize()}",
            callback_data=MonthNavigation(
                action="-",
                current_month=current_month_lower,
                schedule_type=schedule_type,
            ).pack(),
        )
    )

    # Кнопка "Вперед" (только если есть следующий месяц)
    if next_month != current_month_lower:  # Есть следующий месяц
        nav_row.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=MonthNavigation(
                    action="next", current_month=next_month, schedule_type=schedule_type
                ).pack(),
            )
        )

    buttons.append(nav_row)

    # Кнопка "Кратко"
    buttons.append(
        [
            InlineKeyboardButton(
                text="📋 Кратко",
                callback_data=MonthNavigation(
                    action="compact",
                    current_month=current_month_lower,
                    schedule_type=schedule_type,
                ).pack(),
            ),
        ]
    )

    # Кнопки навигации
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="schedule").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def heads_kb(current_date: datetime = None) -> InlineKeyboardMarkup:
    """
    Клавиатура для навигации по руководителям групп

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
            text="◀️",
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
            text="▶️",
            callback_data=HeadNavigation(
                action="next", date=next_date.strftime("%Y-%m-%d")
            ).pack(),
        ),
    ]

    buttons = [nav_row]

    # Добавляем кнопку "Сегодня" если смотрим не сегодняшний день
    if current_date.date() != today:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📍 Сегодня",
                    callback_data=HeadNavigation(
                        action="today", date=today.strftime("%Y-%m-%d")
                    ).pack(),
                ),
            ]
        )

    # Кнопки навигации
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="schedule").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


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


def group_schedule_kb(
    current_date: datetime = None,
    page: int = 1,
    total_pages: int = 1,
    has_prev: bool = False,
    has_next: bool = False,
    user_type: str = "user",
    from_group_mgmt: bool = False,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для группового расписания с навигацией по дням и страницам

    Args:
        current_date: Текущая отображаемая дата
        page: Текущая страница
        total_pages: Общее количество страниц
        has_prev: Есть ли предыдущая страница
        has_next: Есть ли следующая страница
        user_type: Тип пользователя ("head" или "user")
        from_group_mgmt: Вызвано ли из меню управления группой

    Returns:
        Клавиатура с навигацией по дням и страницам
    """
    if current_date is None:
        current_date = get_yekaterinburg_date()

    # Получаем даты для навигации
    prev_date = current_date - timedelta(days=1)
    next_date = current_date + timedelta(days=1)
    today = get_yekaterinburg_date().date()

    # Форматируем дату для отображения
    date_str = current_date.strftime("%d.%m")

    buttons = []

    # Ряд навигации по дням
    nav_row = [
        InlineKeyboardButton(
            text="◀️",
            callback_data=GroupNavigation(
                action="prev",
                date=prev_date.strftime("%Y-%m-%d"),
                page=1,  # Сбрасываем на первую страницу при смене даты
                user_type=user_type,
                from_group_mgmt=from_group_mgmt,
            ).pack(),
        ),
        InlineKeyboardButton(
            text=f"📅 {date_str}",
            callback_data=GroupNavigation(
                action="-",
                date=current_date.strftime("%Y-%m-%d"),
                page=page,
                user_type=user_type,
                from_group_mgmt=from_group_mgmt,
            ).pack(),
        ),
        InlineKeyboardButton(
            text="▶️",
            callback_data=GroupNavigation(
                action="next",
                date=next_date.strftime("%Y-%m-%d"),
                page=1,  # Сбрасываем на первую страницу при смене даты
                user_type=user_type,
                from_group_mgmt=from_group_mgmt,
            ).pack(),
        ),
    ]
    buttons.append(nav_row)

    # Ряд пагинации (если больше одной страницы)
    if total_pages > 1:
        pagination_row = []

        # Кнопка "⏪" (переход к первой странице)
        if page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=GroupNavigation(
                        action="prev_page",
                        date=current_date.strftime("%Y-%m-%d"),
                        page=1,
                        user_type=user_type,
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Кнопка "⬅️" (предыдущая страница)
        if has_prev:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=GroupNavigation(
                        action="prev_page",
                        date=current_date.strftime("%Y-%m-%d"),
                        page=page - 1,
                        user_type=user_type,
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Индикатор страницы
        pagination_row.append(
            InlineKeyboardButton(
                text=f"{page}/{total_pages}",
                callback_data="noop",
            )
        )

        # Кнопка "➡️" (следующая страница)
        if has_next:
            pagination_row.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=GroupNavigation(
                        action="next_page",
                        date=current_date.strftime("%Y-%m-%d"),
                        page=page + 1,
                        user_type=user_type,
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Кнопка "⏭️" (переход к последней странице)
        if page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏭️",
                    callback_data=GroupNavigation(
                        action="next_page",
                        date=current_date.strftime("%Y-%m-%d"),
                        page=total_pages,
                        user_type=user_type,
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Кнопка "Сегодня" если смотрим не сегодняшний день
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
                    ).pack(),
                ),
            ]
        )

    # Кнопки навигации
    if from_group_mgmt:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="↩️ Назад",
                    callback_data=MainMenu(menu="group_management").pack(),
                ),
                InlineKeyboardButton(
                    text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
                ),
            ]
        )
    else:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="↩️ Назад", callback_data=MainMenu(menu="schedule").pack()
                ),
                InlineKeyboardButton(
                    text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
                ),
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)

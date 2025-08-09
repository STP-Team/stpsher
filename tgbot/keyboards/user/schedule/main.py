from typing import List

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.main import MainMenu


class ScheduleMenu(CallbackData, prefix="schedule_menu"):
    menu: str


class MonthNavigation(CallbackData, prefix="month_nav"):
    """Callback data для навигации по месяцам"""

    action: str  # "prev", "next", "select"
    current_month: str  # текущий месяц
    user_type: str = "my"  # "my", "duties", "heads"


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
        ],
        [
            InlineKeyboardButton(
                text="👮‍♂️ Старшие", callback_data=ScheduleMenu(menu="duties").pack()
            ),
            InlineKeyboardButton(
                text="👑 РГ", callback_data=ScheduleMenu(menu="heads").pack()
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
        Следующий месяц
    """
    try:
        current_index = available_months.index(current_month.lower())
        next_index = (current_index + 1) % len(available_months)
        return available_months[next_index]
    except (ValueError, IndexError):
        return available_months[0] if available_months else "январь"


def get_prev_month(current_month: str, available_months: List[str]) -> str:
    """
    Получает предыдущий доступный месяц

    Args:
        current_month: Текущий месяц
        available_months: Список доступных месяцев

    Returns:
        Предыдущий месяц
    """
    try:
        current_index = available_months.index(current_month.lower())
        prev_index = (current_index - 1) % len(available_months)
        return available_months[prev_index]
    except (ValueError, IndexError):
        return available_months[-1] if available_months else "декабрь"


def month_navigation_kb(
    current_month: str, user_type: str = "my"
) -> InlineKeyboardMarkup:
    """
    Клавиатура навигации по месяцам для расписания

    Args:
        current_month: Текущий выбранный месяц
        user_type: Тип пользователя ("my", "duties", "heads")

    Returns:
        Объект встроенной клавиатуры для навигации по месяцам
    """
    available_months = get_available_months()
    current_month = current_month.lower()

    # Получаем предыдущий и следующий месяцы
    prev_month = get_prev_month(current_month, available_months)
    next_month = get_next_month(current_month, available_months)

    # Эмодзи для текущего месяца
    month_emoji = MONTH_EMOJIS.get(current_month, "📅")

    buttons = [
        [
            InlineKeyboardButton(
                text="◀️",
                callback_data=MonthNavigation(
                    action="prev", current_month=prev_month, user_type=user_type
                ).pack(),
            ),
            InlineKeyboardButton(
                text=f"{month_emoji} {current_month.capitalize()}",
                callback_data=MonthNavigation(
                    action="select", current_month=current_month, user_type=user_type
                ).pack(),
            ),
            InlineKeyboardButton(
                text="▶️",
                callback_data=MonthNavigation(
                    action="next", current_month=next_month, user_type=user_type
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="schedule").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Главная", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def schedule_with_month_kb(
    current_month: str, user_type: str = "my"
) -> InlineKeyboardMarkup:
    """
    Объединенная клавиатура: меню расписаний + навигация по месяцам

    Args:
        current_month: Текущий выбранный месяц
        user_type: Тип пользователя

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

    buttons = [
        [
            InlineKeyboardButton(
                text="◀️",
                callback_data=MonthNavigation(
                    action="prev", current_month=prev_month, user_type=user_type
                ).pack(),
            ),
            InlineKeyboardButton(
                text=f"{month_emoji} {current_month.capitalize()}",
                callback_data=MonthNavigation(
                    action="select", current_month=current_month, user_type=user_type
                ).pack(),
            ),
            InlineKeyboardButton(
                text="▶️",
                callback_data=MonthNavigation(
                    action="next", current_month=next_month, user_type=user_type
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Подробнее",
                callback_data=MonthNavigation(
                    action="detailed", current_month=current_month, user_type=user_type
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="schedule").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Главная", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    # Кнопки управления

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

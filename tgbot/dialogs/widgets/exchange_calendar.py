"""Кастомный календарь для биржи подмен с отображением смен."""

from datetime import date

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Calendar, CalendarConfig, CalendarScope
from aiogram_dialog.widgets.kbd.calendar_kbd import (
    CalendarDaysView,
    CalendarMonthView,
    CalendarScopeView,
)
from aiogram_dialog.widgets.text import Format, Text

from tgbot.dialogs.widgets.calendars import RussianMonthNominative, RussianWeekday
from tgbot.misc.dicts import schedule_category_emojis
from tgbot.services.files_processing.core.analyzers import ScheduleAnalyzer


class ShiftDateText(Text):
    """Виджет для отображения даты с эмодзи смены."""

    def __init__(self):
        """Инициализация виджета отображения даты."""
        super().__init__()

    async def _render_text(self, data, dialog_manager: DialogManager) -> str:
        """Рендер даты с эмодзи в зависимости от типа записи в расписании."""
        selected_date: date = data["date"]
        day = selected_date.day
        month = selected_date.month
        year = selected_date.year

        # Получаем данные о сменах из dialog_data
        shift_dates = dialog_manager.dialog_data.get("shift_dates", {})

        # Проверяем есть ли запись на эту дату
        month_day_key = f"{month:02d}_{day:02d}"

        # Для текущего месяца также проверяем простой ключ дня (обратная совместимость)
        from datetime import datetime

        current_date = datetime.now().date()
        day_key = f"{day:02d}"

        schedule_value = None

        # Сначала проверяем специфичный ключ месяца и дня
        if month_day_key in shift_dates:
            shift_data = shift_dates[month_day_key]
            # Извлекаем строку расписания из словаря
            schedule_value = (
                shift_data.get("schedule")
                if isinstance(shift_data, dict)
                else shift_data
            )
        # Только для текущего месяца и года проверяем простой ключ дня
        elif (
            month == current_date.month
            and year == current_date.year
            and day_key in shift_dates
        ):
            shift_data = shift_dates[day_key]
            # Извлекаем строку расписания из словаря
            schedule_value = (
                shift_data.get("schedule")
                if isinstance(shift_data, dict)
                else shift_data
            )

        # Если нет записи, показываем обычный день
        if schedule_value is None:
            return str(day)

        # Категоризируем запись расписания
        category = ScheduleAnalyzer.categorize_schedule_entry(schedule_value)

        # Отображаем день в зависимости от категории
        emoji = schedule_category_emojis.get(category, "")
        if category == "work":
            return f"·{day}·"  # Рабочий день с точками
        elif emoji:
            return f"{emoji}{day}"
        else:  # day_off или неизвестная категория
            return str(day)


class TodayShiftDateText(Text):
    """Виджет для отображения сегодняшней даты с эмодзи смены."""

    def __init__(self):
        """Инициализация виджета сегодняшней даты."""
        super().__init__()

    async def _render_text(self, data, dialog_manager: DialogManager) -> str:
        """Рендер сегодняшней даты с эмодзи в зависимости от типа записи в расписании."""
        selected_date: date = data["date"]
        day = selected_date.day
        month = selected_date.month
        year = selected_date.year

        # Получаем данные о сменах из dialog_data
        shift_dates = dialog_manager.dialog_data.get("shift_dates", {})

        # Проверяем есть ли запись на эту дату
        month_day_key = f"{month:02d}_{day:02d}"

        # Для текущего месяца также проверяем простой ключ дня (обратная совместимость)
        from datetime import datetime

        current_date = datetime.now().date()
        day_key = f"{day:02d}"

        schedule_value = None

        # Сначала проверяем специфичный ключ месяца и дня
        if month_day_key in shift_dates:
            shift_data = shift_dates[month_day_key]
            # Извлекаем строку расписания из словаря
            schedule_value = (
                shift_data.get("schedule")
                if isinstance(shift_data, dict)
                else shift_data
            )
        # Только для текущего месяца и года проверяем простой ключ дня
        elif (
            month == current_date.month
            and year == current_date.year
            and day_key in shift_dates
        ):
            shift_data = shift_dates[day_key]
            # Извлекаем строку расписания из словаря
            schedule_value = (
                shift_data.get("schedule")
                if isinstance(shift_data, dict)
                else shift_data
            )

        # Если нет записи, показываем обычное сегодня
        if schedule_value is None:
            return f"{day}"

        # Категоризируем запись расписания
        category = ScheduleAnalyzer.categorize_schedule_entry(schedule_value)

        # Отображаем сегодняшний день в зависимости от категории
        emoji = schedule_category_emojis.get(category, "")
        if category == "work":
            return f"·︎︎{day}·"  # Рабочий день с точками
        elif emoji:
            return f"{emoji}{day}"
        else:  # day_off или неизвестная категория
            return f"{day}"


class ExchangeCalendar(Calendar):
    """Календарь для биржи подмен с отображением смен пользователя."""

    def __init__(
        self,
        id: str,
        on_click=None,
        config: CalendarConfig = CalendarConfig(min_date=date.today()),
    ):
        """Инициализация календаря биржи подмен.

        Args:
            id: Идентификатор виджета
            on_click: Обработчик выбора даты
            config: Конфигурация календаря
        """
        if config is None:
            config = CalendarConfig(
                firstweekday=0,  # Понедельник первый день недели
            )
        super().__init__(id=id, on_click=on_click, config=config)

    def _init_views(self) -> dict[CalendarScope, CalendarScopeView]:
        """Инициализация кастомных представлений календаря."""
        return {
            CalendarScope.DAYS: CalendarDaysView(
                self._item_callback_data,
                date_text=ShiftDateText(),
                today_text=TodayShiftDateText(),
                header_text="📅 "
                + RussianMonthNominative()
                + " "
                + Format("{date:%Y}"),
                weekday_text=RussianWeekday(),
                next_month_text=RussianMonthNominative() + " ⏩",
                prev_month_text="⏪ " + RussianMonthNominative(),
            ),
            CalendarScope.MONTHS: CalendarMonthView(
                self._item_callback_data,
                month_text=RussianMonthNominative(),
                header_text="📅 Выбор месяца " + Format("{date:%Y}"),
                this_month_text="· " + RussianMonthNominative() + " ·",
                next_year_text=Format("{date:%Y}") + " ⏩",
                prev_year_text="⏪ " + Format("{date:%Y}"),
            ),
        }


class SubscriptionDateText(Text):
    """Виджет для отображения даты в календаре подписок с выделением выбранных дат."""

    def __init__(self):
        """Инициализация виджета отображения даты для подписок."""
        super().__init__()

    async def _render_text(self, data, dialog_manager: DialogManager) -> str:
        """Рендер даты с эмодзи для выбранных дат и категоризацией типа записи."""
        selected_date: date = data["date"]
        day = selected_date.day
        month = selected_date.month
        year = selected_date.year

        # Получаем текущую дату для проверок
        from datetime import datetime

        current_date = datetime.now().date()

        # Получаем данные о сменах из dialog_data
        shift_dates = dialog_manager.dialog_data.get("shift_dates", {})

        # Получаем список выбранных дат для подписки
        selected_dates = dialog_manager.dialog_data.get("selected_dates", [])
        date_str = selected_date.strftime("%Y-%m-%d")
        is_selected = date_str in selected_dates

        # Проверяем есть ли запись на эту дату
        month_day_key = f"{month:02d}_{day:02d}"
        day_key = f"{day:02d}"

        schedule_value = None
        # Сначала проверяем специфичный ключ месяца и дня
        if month_day_key in shift_dates:
            shift_data = shift_dates[month_day_key]
            # Извлекаем строку расписания из словаря
            schedule_value = (
                shift_data.get("schedule")
                if isinstance(shift_data, dict)
                else shift_data
            )
        # Только для текущего месяца и года проверяем простой ключ дня
        elif (
            month == current_date.month
            and year == current_date.year
            and day_key in shift_dates
        ):
            shift_data = shift_dates[day_key]
            # Извлекаем строку расписания из словаря
            schedule_value = (
                shift_data.get("schedule")
                if isinstance(shift_data, dict)
                else shift_data
            )

        # Если нет записи, показываем день как есть (обычный или выбранный)
        if schedule_value is None:
            if is_selected:
                return f"👉{day}"
            else:
                return str(day)

        # Категоризируем запись расписания
        category = ScheduleAnalyzer.categorize_schedule_entry(schedule_value)

        # Формируем отображение даты в зависимости от категории и выбора
        emoji = schedule_category_emojis.get(category, "")

        if is_selected:
            # Выбранные даты с префиксом 👉
            if category == "work":
                return f"👉{day}·"  # Рабочий день с точками
            elif emoji:
                return f"👉{emoji}{day}"
            else:  # day_off
                return f"👉{day}"
        else:
            # Обычные даты без выбора
            if category == "work":
                return f"·{day}·"  # Рабочий день с точками
            elif emoji:
                return f"{emoji}{day}"
            else:  # day_off
                return str(day)


class SubscriptionTodayDateText(Text):
    """Виджет для отображения сегодняшней даты в календаре подписок."""

    def __init__(self):
        """Инициализация виджета сегодняшней даты для подписок."""
        super().__init__()

    async def _render_text(self, data, dialog_manager: DialogManager) -> str:
        """Рендер сегодняшней даты с категоризацией и выделением если она выбрана."""
        selected_date: date = data["date"]
        day = selected_date.day
        month = selected_date.month
        year = selected_date.year

        # Получаем данные о сменах из dialog_data
        shift_dates = dialog_manager.dialog_data.get("shift_dates", {})

        # Получаем список выбранных дат для подписки
        selected_dates = dialog_manager.dialog_data.get("selected_dates", [])
        date_str = selected_date.strftime("%Y-%m-%d")
        is_selected = date_str in selected_dates

        # Проверяем есть ли запись на эту дату
        month_day_key = f"{month:02d}_{day:02d}"
        day_key = f"{day:02d}"

        schedule_value = None
        # Сначала проверяем специфичный ключ месяца и дня
        if month_day_key in shift_dates:
            shift_data = shift_dates[month_day_key]
            # Извлекаем строку расписания из словаря
            schedule_value = (
                shift_data.get("schedule")
                if isinstance(shift_data, dict)
                else shift_data
            )
        # Для текущего месяца также проверяем простой ключ дня (обратная совместимость)
        from datetime import datetime

        current_date = datetime.now().date()
        if (
            month == current_date.month
            and year == current_date.year
            and day_key in shift_dates
        ):
            shift_data = shift_dates[day_key]
            # Извлекаем строку расписания из словаря
            schedule_value = (
                shift_data.get("schedule")
                if isinstance(shift_data, dict)
                else shift_data
            )

        # Если нет записи, показываем сегодняшний день как есть
        if schedule_value is None:
            if is_selected:
                return f"🟢{day}"
            else:
                return f"{day}"

        # Категоризируем запись расписания
        category = ScheduleAnalyzer.categorize_schedule_entry(schedule_value)

        # Формируем отображение сегодняшней даты в зависимости от категории и выбора
        emoji = schedule_category_emojis.get(category, "")

        if is_selected:
            # Выбранные сегодняшние даты с зеленым кружком
            if category == "work":
                return f"🟢{day}·"  # Рабочий день с точками
            elif emoji:
                return f"🟢{emoji}{day}"
            else:  # day_off
                return f"🟢{day}"
        else:
            # Обычные сегодняшние даты
            if category == "work":
                return f"·{day}·"  # Рабочий день с точками
            elif emoji:
                return f"{emoji}{day}"
            else:  # day_off
                return f"{day}"


class SubscriptionCalendar(Calendar):
    """Календарь для подписок с выделением выбранных дат и блокировкой прошедших."""

    def __init__(
        self,
        id: str,
        on_click=None,
        config: CalendarConfig = CalendarConfig(min_date=date.today()),
    ):
        """Инициализация календаря подписок.

        Args:
            id: Идентификатор виджета
            on_click: Обработчик выбора даты
            config: Конфигурация календаря
        """
        if config is None:
            config = CalendarConfig(
                firstweekday=0,  # Понедельник первый день недели
            )
        super().__init__(id=id, on_click=on_click, config=config)

    def _init_views(self) -> dict[CalendarScope, CalendarScopeView]:
        """Инициализация кастомных представлений календаря для подписок."""
        return {
            CalendarScope.DAYS: CalendarDaysView(
                self._item_callback_data,
                date_text=SubscriptionDateText(),
                today_text=SubscriptionTodayDateText(),
                header_text="📅 "
                + RussianMonthNominative()
                + " "
                + Format("{date:%Y}"),
                weekday_text=RussianWeekday(),
                next_month_text=RussianMonthNominative() + " ⏩",
                prev_month_text="⏪ " + RussianMonthNominative(),
            ),
            CalendarScope.MONTHS: CalendarMonthView(
                self._item_callback_data,
                month_text=RussianMonthNominative(),
                header_text="📅 Выбор месяца " + Format("{date:%Y}"),
                this_month_text="· " + RussianMonthNominative() + " ·",
                next_year_text=Format("{date:%Y}") + " ⏩",
                prev_year_text="⏪ " + Format("{date:%Y}"),
            ),
        }

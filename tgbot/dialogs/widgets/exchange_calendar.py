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


class ShiftDateText(Text):
    """Виджет для отображения даты с эмодзи смены."""

    def __init__(self):
        """Инициализация виджета отображения даты."""
        super().__init__()

    async def _render_text(self, data, dialog_manager: DialogManager) -> str:
        """Рендер даты с эмодзи смены если она есть."""
        selected_date: date = data["date"]
        day = selected_date.day

        # Получаем данные о сменах из dialog_data
        shift_dates = dialog_manager.dialog_data.get("shift_dates", {})

        # Проверяем есть ли смена на эту дату
        date_key = f"{day:02d}"
        if date_key in shift_dates:
            return f"·{day}·"

        return str(day)


class TodayShiftDateText(Text):
    """Виджет для отображения сегодняшней даты с эмодзи смены."""

    def __init__(self):
        """Инициализация виджета сегодняшней даты."""
        super().__init__()

    async def _render_text(self, data, dialog_manager: DialogManager) -> str:
        """Рендер сегодняшней даты с эмодзи смены если она есть."""
        selected_date: date = data["date"]
        day = selected_date.day

        # Получаем данные о сменах из dialog_data
        shift_dates = dialog_manager.dialog_data.get("shift_dates", {})

        # Проверяем есть ли смена на эту дату
        date_key = f"{day:02d}"
        if date_key in shift_dates:
            return f"·︎︎{day}·"

        return f"{day}"


class ExchangeCalendar(Calendar):
    """Календарь для биржи подмен с отображением смен пользователя."""

    def __init__(
        self,
        id: str,
        on_click=None,
        config: CalendarConfig = None,
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

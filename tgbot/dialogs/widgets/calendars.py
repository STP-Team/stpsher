"""Кастомный календарь с русской локализацией."""

from datetime import date

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Calendar, CalendarConfig, CalendarScope
from aiogram_dialog.widgets.kbd.calendar_kbd import (
    DATE_TEXT,
    CalendarDaysView,
    CalendarMonthView,
    CalendarScopeView,
)
from aiogram_dialog.widgets.text import Format, Text

from tgbot.misc.dicts import russian_months_nominative, russian_weekdays_short


class RussianWeekday(Text):
    """Виджет для отображения дня недели на русском."""

    async def _render_text(self, data, dialog_manager: DialogManager) -> str:
        """Рендер названия дня недели на русском.

        Args:
            data: Данные с датой
            dialog_manager: Менеджер диалога

        Returns:
            Русское сокращение дня недели
        """
        selected_date: date = data["date"]
        return russian_weekdays_short[selected_date.weekday()]


class RussianMonthNominative(Text):
    """Виджет для отображения месяца на русском в именительном падеже."""

    async def _render_text(self, data, dialog_manager: DialogManager) -> str:
        """Рендер названия месяца на русском в именительном падеже.

        Args:
            data: Данные с датой
            dialog_manager: Менеджер диалога

        Returns:
            Русское название месяца в именительном падеже
        """
        selected_date: date = data["date"]
        return russian_months_nominative[selected_date.month]


class RussianCalendar(Calendar):
    """Календарь с русской локализацией."""

    def __init__(
        self,
        id: str,
        on_click=None,
        config: CalendarConfig = None,
    ):
        """Инициализация русского календаря.

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
        """Инициализация кастомных представлений календаря.

        Returns:
            Словарь представлений календаря
        """
        return {
            CalendarScope.DAYS: CalendarDaysView(
                self._item_callback_data,
                date_text=DATE_TEXT,
                today_text="· " + Format("{date:%d}") + " ·",
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

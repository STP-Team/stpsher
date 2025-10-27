"""Геттеры для настроек раздела Покупки на бирже."""

from typing import Any, Dict

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import ManagedRadio, ManagedToggle


async def buy_settings_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для получения выбранных пользователем настроек биржи.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь настроек биржи
    """
    day_filter_checkbox: ManagedRadio = dialog_manager.find("day_filter")
    day_filter_value = day_filter_checkbox.get_checked()

    shift_filter_checkbox: ManagedRadio = dialog_manager.find("shift_filter")
    shift_filter_value = shift_filter_checkbox.get_checked()

    date_sort_toggle: ManagedToggle = dialog_manager.find("date_sort")
    date_sort_value = date_sort_toggle.get_checked()

    price_sort_toggle: ManagedToggle = dialog_manager.find("price_sort")
    price_sort_value = price_sort_toggle.get_checked()

    return {
        "day_filter": day_filter_value,
        "shift_filter": shift_filter_value,
        "date_sort": date_sort_value,
        "price_sort": price_sort_value,
    }


async def buy_filters_day_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для фильтров по дню для покупок на бирже.

    Args:
        dialog_manager:
        **_kwargs:

    Returns:
        Список фильтров по дню
    """
    day_filter_options = [
        ("all", "Все"),
        ("today", "Сегодня"),
        ("tomorrow", "Завтра"),
    ]

    filter_checkbox: ManagedRadio = dialog_manager.find("day_filter")
    filter_value = None
    if filter_checkbox:
        filter_value = filter_checkbox.get_checked()

    filter_description = ""
    match filter_value:
        case None:
            filter_description = ""
        case "all":
            filter_description = ""
        case "all":
            filter_description = ""
        case "today":
            filter_description = "<i>Текущий фильтр: Только предложения на сегодня</i>"
        case "tomorrow":
            filter_description = "<i>Текущий фильтр: Только предложения на завтра</i>"

    return {
        "day_filter_options": day_filter_options,
        "filter_description": filter_description,
    }


async def buy_filters_shift_getter() -> Dict[str, Any]:
    """Геттер для фильтров по смене для покупок на бирже.

    Returns:
        Список фильтров по смене
    """
    shift_filter_options = [
        ("all", "Все"),
        ("no_shift", "Нет смены"),
        ("shift", "Есть смена"),
    ]

    return {
        "shift_filter_options": shift_filter_options,
    }

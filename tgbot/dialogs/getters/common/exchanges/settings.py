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
    day_filter_value = (
        day_filter_checkbox.get_checked() if day_filter_checkbox else "all"
    )

    shift_filter_checkbox: ManagedRadio = dialog_manager.find("shift_filter")
    shift_filter_value = (
        shift_filter_checkbox.get_checked() if shift_filter_checkbox else "all"
    )

    date_sort_toggle: ManagedToggle = dialog_manager.find("date_sort")
    date_sort_value = date_sort_toggle.get_checked() if date_sort_toggle else "nearest"

    price_sort_toggle: ManagedToggle = dialog_manager.find("price_sort")
    price_sort_value = price_sort_toggle.get_checked() if price_sort_toggle else "cheap"

    # Преобразуем значения в читаемый текст
    day_filter_text = {
        "all": "Все дни",
        "today": "Только сегодня",
        "tomorrow": "Только завтра",
        "current_week": "Текущая неделя",
        "current_month": "Текущий месяц",
    }.get(day_filter_value, "Все дни")

    shift_filter_text = {
        "all": "Все смены",
        "no_shift": "Без смены",
        "shift": "Со сменой",
    }.get(shift_filter_value, "Без смены")

    date_sort_text = {
        "nearest": "Сначала ближайшие",
        "far": "Сначала дальние",
    }.get(date_sort_value, "Сначала ближайшие")

    price_sort_text = {
        "cheap": "Сначала дешевые",
        "expensive": "Сначала дорогие",
    }.get(price_sort_value, "Сначала дешевые")

    # Определяем, отличаются ли настройки от значений по умолчанию
    is_default_settings = (
        day_filter_value == "all"
        and shift_filter_value == "all"
        and date_sort_value == "nearest"
        and price_sort_value == "cheap"
    )

    return {
        "day_filter": day_filter_text,
        "shift_filter": shift_filter_text,
        "date_sort": date_sort_text,
        "price_sort": price_sort_text,
        "show_reset_button": not is_default_settings,
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
        ("current_week", "Текущая неделя"),
        ("current_month", "Текущий месяц"),
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
        case "today":
            filter_description = "<i>Текущий фильтр: Только предложения на сегодня</i>"
        case "tomorrow":
            filter_description = "<i>Текущий фильтр: Только предложения на завтра</i>"
        case "current_week":
            filter_description = (
                "<i>Текущий фильтр: Только предложения на текущей неделе</i>"
            )
        case "current_month":
            filter_description = (
                "<i>Текущий фильтр: Только предложения в текущем месяце</i>"
            )

    # Определяем, отличается ли фильтр от значения по умолчанию
    show_reset_filters = filter_value is not None and filter_value != "all"

    return {
        "day_filter_options": day_filter_options,
        "filter_description": filter_description,
        "show_reset_filters": show_reset_filters,
    }


async def buy_filters_shift_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для фильтров по смене для покупок на бирже.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Список фильтров по смене
    """
    shift_filter_options = [
        ("all", "Все"),
        ("no_shift", "Нет смены"),
        ("shift", "Есть смена"),
    ]

    # Получаем текущее значение фильтра
    filter_checkbox: ManagedRadio = dialog_manager.find("shift_filter")
    filter_value = None
    if filter_checkbox:
        filter_value = filter_checkbox.get_checked()

    # Определяем, отличается ли фильтр от значения по умолчанию
    show_reset_filters = filter_value is not None and filter_value != "all"

    return {
        "shift_filter_options": shift_filter_options,
        "show_reset_filters": show_reset_filters,
    }

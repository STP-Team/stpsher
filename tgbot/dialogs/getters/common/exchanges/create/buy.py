from datetime import datetime
from typing import Any, Dict

from aiogram_dialog import DialogManager


async def buy_date_getter(dialog_manager: DialogManager, **_kwargs) -> Dict[str, Any]:
    """Геттер для окна выбора даты покупки."""
    return {}


async def buy_hours_getter(dialog_manager: DialogManager, **_kwargs) -> Dict[str, Any]:
    """Геттер для окна ввода времени покупки."""
    buy_date = dialog_manager.dialog_data.get("buy_date")
    any_date = dialog_manager.dialog_data.get("any_date", False)

    result = {}

    if buy_date:
        date_obj = datetime.fromisoformat(buy_date).date()
        formatted_date = date_obj.strftime("%d.%m.%Y")
        result["selected_date"] = formatted_date
    elif any_date:
        result["any_date"] = True

    return result


async def buy_price_getter(dialog_manager: DialogManager, **_kwargs) -> Dict[str, Any]:
    """Геттер для окна ввода цены покупки."""
    data = dialog_manager.dialog_data

    buy_date = data.get("buy_date")
    any_date = data.get("any_date", False)
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    any_hours = data.get("any_hours", False)

    result = {}

    # Дата
    if buy_date:
        date_obj = datetime.fromisoformat(buy_date).date()
        formatted_date = date_obj.strftime("%d.%m.%Y")
        result["selected_date"] = formatted_date
    elif any_date:
        result["any_date"] = True

    # Время
    if start_time and end_time:
        start_time_str = (
            start_time.split("T")[1][:5] if "T" in start_time else start_time
        )
        end_time_str = end_time.split("T")[1][:5] if "T" in end_time else end_time
        result["hours_range"] = f"{start_time_str}-{end_time_str}"
    elif any_hours:
        result["any_hours"] = True

    return result


async def buy_comment_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна ввода комментария покупки."""
    data = dialog_manager.dialog_data

    buy_date = data.get("buy_date")
    any_date = data.get("any_date", False)
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    any_hours = data.get("any_hours", False)
    price_per_hour = data.get("buy_price_per_hour", 0)

    result = {"price_per_hour": price_per_hour}

    # Дата
    if buy_date:
        date_obj = datetime.fromisoformat(buy_date).date()
        formatted_date = date_obj.strftime("%d.%m.%Y")
        result["selected_date"] = formatted_date
    elif any_date:
        result["any_date"] = True

    # Время
    if start_time and end_time:
        start_time_str = (
            start_time.split("T")[1][:5] if "T" in start_time else start_time
        )
        end_time_str = end_time.split("T")[1][:5] if "T" in end_time else end_time
        result["hours_range"] = f"{start_time_str}-{end_time_str}"
    elif any_hours:
        result["any_hours"] = True

    return result


async def buy_confirmation_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна подтверждения покупки."""
    data = dialog_manager.dialog_data

    buy_date = data.get("buy_date")
    any_date = data.get("any_date", False)
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    any_hours = data.get("any_hours", False)
    price_per_hour = data.get("buy_price_per_hour", 0)
    comment = data.get("buy_comment")

    # Информация о дате
    if buy_date:
        date_obj = datetime.fromisoformat(buy_date).date()
        date_info = date_obj.strftime("%d.%m.%Y")
    else:
        date_info = "Любая дата"

    # Информация о времени
    if start_time and end_time:
        start_time_str = (
            start_time.split("T")[1][:5] if "T" in start_time else start_time
        )
        end_time_str = end_time.split("T")[1][:5] if "T" in end_time else end_time
        time_info = f"{start_time_str}-{end_time_str}"
    else:
        time_info = "Любое время"

    result = {
        "date_info": date_info,
        "time_info": time_info,
        "price_per_hour": price_per_hour,
    }

    # Добавляем комментарий если есть
    if comment:
        result["comment"] = comment

    return result

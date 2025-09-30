from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from tgbot.misc.states.dialogs.head import HeadSG
from tgbot.misc.states.dialogs.user import UserSG
from tgbot.services.schedule.schedule_handlers import schedule_service


async def prev_day(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    from datetime import datetime, timedelta

    current_date_str = dialog_manager.dialog_data.get("current_date")
    if current_date_str is None:
        current_date = schedule_service.get_current_date()
    else:
        current_date = datetime.fromisoformat(current_date_str)

    prev_date = current_date - timedelta(days=1)
    dialog_manager.dialog_data["current_date"] = prev_date.isoformat()


async def next_day(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    from datetime import datetime, timedelta

    current_date_str = dialog_manager.dialog_data.get("current_date")
    if current_date_str is None:
        current_date = schedule_service.get_current_date()
    else:
        current_date = datetime.fromisoformat(current_date_str)

    next_date = current_date + timedelta(days=1)
    dialog_manager.dialog_data["current_date"] = next_date.isoformat()


async def today(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    today_date = schedule_service.get_current_date()
    dialog_manager.dialog_data["current_date"] = today_date.isoformat()


async def prev_month(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    current_month = dialog_manager.dialog_data.get("current_month", "сентябрь")
    prev_month_name = get_prev_month(current_month)
    dialog_manager.dialog_data["current_month"] = prev_month_name


async def next_month(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    current_month = dialog_manager.dialog_data.get("current_month", "сентябрь")
    next_month_name = get_next_month(current_month)
    dialog_manager.dialog_data["current_month"] = next_month_name


async def do_nothing(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    pass


async def clear_and_switch_to_duties(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Clear date data and switch to duties schedule"""
    dialog_manager.dialog_data.pop("current_date", None)

    current_state = dialog_manager.current_context().state
    match current_state:
        case UserSG.schedule:
            await dialog_manager.switch_to(UserSG.schedule_duties)
        case HeadSG.schedule:
            await dialog_manager.switch_to(HeadSG.schedule_duties)


async def clear_and_switch_to_group(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Clear date data and switch to group schedule"""
    dialog_manager.dialog_data.pop("current_date", None)

    current_state = dialog_manager.current_context().state
    match current_state:
        case UserSG.schedule:
            await dialog_manager.switch_to(UserSG.schedule_group)
        case HeadSG.schedule:
            await dialog_manager.switch_to(HeadSG.schedule_group)


async def clear_and_switch_to_heads(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Clear date data and switch to heads schedule"""
    dialog_manager.dialog_data.pop("current_date", None)

    current_state = dialog_manager.current_context().state
    match current_state:
        case UserSG.schedule:
            await dialog_manager.switch_to(UserSG.schedule_heads)
        case HeadSG.schedule:
            await dialog_manager.switch_to(HeadSG.schedule_heads)


async def clear_and_switch_to_my(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Clear month data and switch to my schedule"""
    dialog_manager.dialog_data.pop("current_month", None)

    current_state = dialog_manager.current_context().state
    match current_state:
        case UserSG.schedule:
            await dialog_manager.switch_to(UserSG.schedule_my)
        case HeadSG.schedule:
            await dialog_manager.switch_to(HeadSG.schedule_my)


def get_prev_month(current_month: str) -> str:
    """Get the previous month name in Russian"""
    months = [
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
    try:
        current_index = months.index(current_month.lower())
        prev_index = (current_index - 1) % 12
        return months[prev_index]
    except ValueError:
        return "сентябрь"


def get_next_month(current_month: str) -> str:
    """Get the next month name in Russian"""
    months = [
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
    try:
        current_index = months.index(current_month.lower())
        next_index = (current_index + 1) % 12
        return months[next_index]
    except ValueError:
        return "сентябрь"

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from tgbot.handlers.user.schedule.main import ScheduleHandlerService

schedule_service = ScheduleHandlerService()


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
    from tgbot.keyboards.user.schedule.main import get_prev_month

    current_month = dialog_manager.dialog_data.get("current_month", "сентябрь")
    prev_month_name = get_prev_month(current_month)
    dialog_manager.dialog_data["current_month"] = prev_month_name


async def next_month(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    from tgbot.keyboards.user.schedule.main import get_next_month

    current_month = dialog_manager.dialog_data.get("current_month", "сентябрь")
    next_month_name = get_next_month(current_month)
    dialog_manager.dialog_data["current_month"] = next_month_name


async def do_nothing(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    pass

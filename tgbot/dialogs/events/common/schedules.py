"""Обработчики для функций графиков."""

import datetime
from datetime import date

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from tgbot.dialogs.states.common.exchanges import Exchanges
from tgbot.dialogs.states.common.schedule import Schedules
from tgbot.dialogs.widgets import RussianCalendar
from tgbot.misc.dicts import russian_months
from tgbot.services.files_processing.formatters.schedule import (
    get_current_date,
    get_current_month,
)


async def start_schedules_dialog(
    _callback: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик перехода в диалог графиков.

    Args:
        _callback: Callback query от Telegram
        _widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.start(
        Schedules.menu,
    )


async def open_my_exchanges(
    _callback: CallbackQuery, _widget: Button, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Открываем сделки пользователя.

    Args:
        _callback: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.start(Exchanges.my)


async def prev_day(
    _callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
) -> None:
    """Получает предыдущий день и сохраняет его в dialog_data.

    Args:
        _button: Данные кнопки смены дня
        _callback: Callback query от Telegram
        dialog_manager: Менеджер диалога
    """
    current_date_str = dialog_manager.dialog_data.get("current_date")
    if current_date_str is None:
        current_date = get_current_date()
    else:
        current_date = datetime.datetime.fromisoformat(current_date_str)

    prev_date = current_date - datetime.timedelta(days=1)
    dialog_manager.dialog_data["current_date"] = prev_date.isoformat()


async def next_day(
    _callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
) -> None:
    """Получает следующий день и сохраняет его в dialog_data.

    Args:
        _button: Данные кнопки смены дня
        _callback: Callback query от Telegram
        dialog_manager: Менеджер диалога
    """
    current_date_str = dialog_manager.dialog_data.get("current_date")
    if current_date_str is None:
        current_date = get_current_date()
    else:
        current_date = datetime.datetime.fromisoformat(current_date_str)

    next_date = current_date + datetime.timedelta(days=1)
    dialog_manager.dialog_data["current_date"] = next_date.isoformat()


async def today(
    _callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
) -> None:
    """Получает текущий день и сохраняет его в dialog_data.

    Args:
        _button: Данные кнопки смены дня
        _callback: Callback query от Telegram
        dialog_manager: Менеджер диалога
    """
    today_date = get_current_date()
    dialog_manager.dialog_data["current_date"] = today_date.isoformat()


async def prev_month(
    _callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
) -> None:
    """Получает предыдущий месяц и сохраняет его в dialog_data.

    Args:
        _callback: Callback query от Telegram
        _button: Данные кнопки смены дня
        dialog_manager: Менеджер диалога
    """
    current_month = dialog_manager.dialog_data.get("current_month", get_current_month())
    prev_month_name = get_prev_month(current_month)
    dialog_manager.dialog_data["current_month"] = prev_month_name


async def next_month(
    _callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
) -> None:
    """Получает следующий месяц и сохраняет его в dialog_data.

    Args:
        _callback: Callback query от Telegram
        _button: Данные кнопки смены дня
        dialog_manager: Менеджер диалога
    """
    current_month = dialog_manager.dialog_data.get("current_month", get_current_month())
    next_month_name = get_next_month(current_month)
    dialog_manager.dialog_data["current_month"] = next_month_name


async def do_nothing(
    _callback: CallbackQuery, _button: Button, _dialog_manager: DialogManager
) -> None:
    """Делает ничего.

    Args:
        _callback: Callback query от Telegram
        _button: Данные кнопки смены дня
        _dialog_manager: Менеджер диалога
    """
    pass


def get_prev_month(current_month: str) -> str:
    """Получает название предыдущего месяца.

    Args:
        current_month: Название текущего месяца

    Returns:
        Название предыдущего месяца
    """
    month_to_num = {name: num for num, name in russian_months.items()}

    # Получаем номер текущего месяца
    current_num = month_to_num.get(current_month.lower())

    # Считаем номер предыдущего месяца (1-12)
    prev_num = 12 if current_num == 1 else current_num - 1
    return russian_months[prev_num]


def get_next_month(current_month: str) -> str:
    """Получает название следующего месяца.

    Args:
        current_month: Название текущего месяца

    Returns:
        Название следующего месяца
    """
    month_to_num = {name: num for num, name in russian_months.items()}

    # Получаем номер текущего месяца
    current_num = month_to_num.get(current_month.lower())

    # Считаем номер предыдущего месяца (1-12)
    prev_num = 1 if current_num == 12 else current_num + 1
    return russian_months[prev_num]


async def on_date_selected(
    _callback: CallbackQuery,
    _widget: RussianCalendar,
    dialog_manager: DialogManager,
    selected_date: date,
) -> None:
    """Обработчик выбора даты в календаре.

    Args:
        _callback: Callback query от Telegram
        _widget: Виджет календаря
        dialog_manager: Менеджер диалога
        selected_date: Выбранная дата
    """
    # Сохраняем выбранную дату в dialog_data
    dialog_manager.dialog_data["current_date"] = selected_date.isoformat()

    # Возвращаемся к соответствующему окну в зависимости от текущего состояния
    current_state = dialog_manager.current_context().state
    if current_state == Schedules.duties_calendar:
        await dialog_manager.switch_to(Schedules.duties)
    elif current_state == Schedules.group_calendar:
        await dialog_manager.switch_to(Schedules.group)
    elif current_state == Schedules.heads_calendar:
        await dialog_manager.switch_to(Schedules.heads)

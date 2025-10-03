"""Общие функции для окон графиков."""

import datetime

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from tgbot.misc.dicts import russian_months
from tgbot.misc.states.dialogs.head import HeadSG
from tgbot.misc.states.dialogs.user import UserSG
from tgbot.services.schedule.schedule_handlers import schedule_service


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
        current_date = schedule_service.get_current_date()
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
        current_date = schedule_service.get_current_date()
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
    today_date = schedule_service.get_current_date()
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
    current_month = dialog_manager.dialog_data.get(
        "current_month", schedule_service.get_current_month()
    )
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
    current_month = dialog_manager.dialog_data.get(
        "current_month", schedule_service.get_current_month()
    )
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


async def clear_and_switch_to_my(
    _callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
) -> None:
    """Заменяет current_month в dialog_data на текущий месяц.

    Открывает окно графика сотрудника

    Args:
        _callback: Callback query от Telegram
        _button: Данные кнопки смены дня
        dialog_manager: Менеджер диалога
    """
    # Устанавливаем current_month в dialog_data на текущий месяц
    dialog_manager.dialog_data["current_month"] = schedule_service.get_current_month()

    # Устанавливаем режим отображения на компактный если на установлено иначе
    dialog_manager.dialog_data.setdefault("schedule_mode", "compact")

    current_state = dialog_manager.current_context().state
    match current_state:
        case UserSG.schedule:
            await dialog_manager.switch_to(UserSG.schedule_my)
        case HeadSG.schedule:
            await dialog_manager.switch_to(HeadSG.schedule_my)


async def clear_and_switch_to_duties(
    _callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
) -> None:
    """Заменяет current_date в dialog_data на текущую дату.

    Открывает окно графика дежурных в зависимости от роли пользователя

    Args:
        _callback: Callback query от Telegram
        _button: Данные кнопки смены дня
        dialog_manager: Менеджер диалога
    """
    # Устанавливаем current_date в dialog_data на сегодня
    dialog_manager.dialog_data["current_date"] = (
        schedule_service.get_current_date().isoformat()
    )

    current_state = dialog_manager.current_context().state
    match current_state:
        case UserSG.schedule:
            await dialog_manager.switch_to(UserSG.schedule_duties)
        case HeadSG.schedule:
            await dialog_manager.switch_to(HeadSG.schedule_duties)


async def clear_and_switch_to_group(
    _callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
) -> None:
    """Заменяет current_date в dialog_data на текущую дату.

    Открывает окно графика группы в зависимости от роли пользователя

    Args:
        _callback: Callback query от Telegram
        _button: Данные кнопки смены дня
        dialog_manager: Менеджер диалога
    """
    # Устанавливаем current_date в dialog_data на сегодня
    dialog_manager.dialog_data["current_date"] = (
        schedule_service.get_current_date().isoformat()
    )

    current_state = dialog_manager.current_context().state
    match current_state:
        case UserSG.schedule:
            await dialog_manager.switch_to(UserSG.schedule_group)
        case HeadSG.schedule:
            await dialog_manager.switch_to(HeadSG.schedule_group)


async def clear_and_switch_to_heads(
    _callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
):
    """Заменяет current_date в dialog_data на текущую дату.

    Открывает окно графика руководителей в зависимости от роли пользователя

    Args:
        _callback: Callback query от Telegram
        _button: Данные кнопки смены дня
        dialog_manager: Менеджер диалога
    """
    # Устанавливаем current_date в dialog_data на сегодня
    dialog_manager.dialog_data["current_date"] = (
        schedule_service.get_current_date().isoformat()
    )

    current_state = dialog_manager.current_context().state
    match current_state:
        case UserSG.schedule:
            await dialog_manager.switch_to(UserSG.schedule_heads)
        case HeadSG.schedule:
            await dialog_manager.switch_to(HeadSG.schedule_heads)


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

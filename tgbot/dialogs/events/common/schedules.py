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
from tgbot.services.files_processing.utils.time_parser import (
    get_current_date,
    get_current_month,
)


async def start_schedules_dialog(
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик перехода в диалог графиков.

    Args:
        _event: Callback query от Telegram
        _widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.start(
        Schedules.menu,
    )


async def open_my_exchanges(
    _event: CallbackQuery, _widget: Button, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Открываем сделки пользователя.

    Args:
        _event: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.start(Exchanges.my)


async def prev_day(
    _event: CallbackQuery, _widget: Button, dialog_manager: DialogManager
) -> None:
    """Получает предыдущий день и сохраняет его в dialog_data.

    Args:
        _widget: Данные кнопки смены дня
        _event: Callback query от Telegram
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
    _event: CallbackQuery, _widget: Button, dialog_manager: DialogManager
) -> None:
    """Получает следующий день и сохраняет его в dialog_data.

    Args:
        _widget: Данные кнопки смены дня
        _event: Callback query от Telegram
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
    _event: CallbackQuery, _widget: Button, dialog_manager: DialogManager
) -> None:
    """Получает текущий день и сохраняет его в dialog_data.

    Args:
        _widget: Данные кнопки смены дня
        _event: Callback query от Telegram
        dialog_manager: Менеджер диалога
    """
    today_date = get_current_date()
    dialog_manager.dialog_data["current_date"] = today_date.isoformat()


async def prev_month(
    _event: CallbackQuery, _widget: Button, dialog_manager: DialogManager
) -> None:
    """Получает предыдущий месяц и сохраняет его в dialog_data.

    Args:
        _event: Callback query от Telegram
        _widget: Данные кнопки смены дня
        dialog_manager: Менеджер диалога
    """
    current_month = dialog_manager.dialog_data.get("current_month", get_current_month())
    current_year = dialog_manager.dialog_data.get(
        "current_year", datetime.datetime.now().year
    )
    prev_month_name, prev_year = get_prev_month(current_month, current_year)
    dialog_manager.dialog_data["current_month"] = prev_month_name
    dialog_manager.dialog_data["current_year"] = prev_year


async def next_month(
    _event: CallbackQuery, _widget: Button, dialog_manager: DialogManager
) -> None:
    """Получает следующий месяц и сохраняет его в dialog_data.

    Args:
        _event: Callback query от Telegram
        _widget: Данные кнопки смены дня
        dialog_manager: Менеджер диалога
    """
    current_month = dialog_manager.dialog_data.get("current_month", get_current_month())
    current_year = dialog_manager.dialog_data.get(
        "current_year", datetime.datetime.now().year
    )
    next_month_name, next_year = get_next_month(current_month, current_year)
    dialog_manager.dialog_data["current_month"] = next_month_name
    dialog_manager.dialog_data["current_year"] = next_year


async def do_nothing(
    _event: CallbackQuery, _widget: Button, _dialog_manager: DialogManager
) -> None:
    """Делает ничего.

    Args:
        _event: Callback query от Telegram
        _widget: Данные кнопки смены дня
        _dialog_manager: Менеджер диалога
    """
    pass


def get_prev_month(current_month: str, current_year: int) -> tuple[str, int]:
    """Получает название предыдущего месяца и год.

    Args:
        current_month: Название текущего месяца
        current_year: Текущий год

    Returns:
        Кортеж (название_предыдущего_месяца, год)
    """
    month_to_num = {name: num for num, name in russian_months.items()}

    # Получаем номер текущего месяца
    current_num = month_to_num.get(current_month.lower())

    # Считаем номер предыдущего месяца (1-12)
    prev_num = 12 if current_num == 1 else current_num - 1

    # Если переходим с января на декабрь, уменьшаем год
    prev_year = current_year - 1 if current_num == 1 else current_year

    return russian_months[prev_num], prev_year


def get_next_month(current_month: str, current_year: int) -> tuple[str, int]:
    """Получает название следующего месяца и год.

    Args:
        current_month: Название текущего месяца
        current_year: Текущий год

    Returns:
        Кортеж (название_следующего_месяца, год)
    """
    month_to_num = {name: num for num, name in russian_months.items()}

    # Получаем номер текущего месяца
    current_num = month_to_num.get(current_month.lower())

    # Считаем номер следующего месяца (1-12)
    next_num = 1 if current_num == 12 else current_num + 1

    # Если переходим с декабря на январь, увеличиваем год
    next_year = current_year + 1 if current_num == 12 else current_year

    return russian_months[next_num], next_year


async def on_date_selected(
    _event: CallbackQuery,
    _widget: RussianCalendar,
    dialog_manager: DialogManager,
    selected_date: date,
) -> None:
    """Обработчик выбора даты в календаре.

    Args:
        _event: Callback query от Telegram
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
    elif current_state == Schedules.tutors_calendar:
        await dialog_manager.switch_to(Schedules.tutors)


async def switch_to_calendar_view(
    _event: CallbackQuery, _widget: Button, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Переключение в календарный вид с синхронизацией месяца.

    Args:
        _event: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    # Получаем текущий месяц и год из текстового вида
    current_month = dialog_manager.dialog_data.get("current_month", get_current_month())
    current_year = dialog_manager.dialog_data.get(
        "current_year", datetime.datetime.now().year
    )

    # Переключаемся в календарный вид
    await dialog_manager.switch_to(Schedules.my_calendar)

    # Синхронизируем месяц в календаре
    calendar_widget = dialog_manager.find("my_schedule_calendar")
    if calendar_widget and current_month:
        # Находим номер месяца
        month_to_num = {name.lower(): num for num, name in russian_months.items()}
        month_num = month_to_num.get(current_month.lower())
        if month_num:
            from datetime import date

            # Устанавливаем offset календаря на нужный месяц и год
            target_date = date(current_year, month_num, 1)
            calendar_widget.set_offset(target_date)


async def switch_to_text_view(
    _event: CallbackQuery, _widget: Button, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Переключение в текстовый вид с синхронизацией месяца.

    Args:
        _event: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    # Получаем текущий месяц и год из календарного вида
    calendar_widget = dialog_manager.find("my_schedule_calendar")
    if calendar_widget:
        try:
            current_offset = calendar_widget.get_offset()
            if current_offset:
                displayed_month_name = russian_months.get(current_offset.month)
                displayed_year = current_offset.year
                if displayed_month_name:
                    # Сохраняем выбранный месяц и год для текстового вида
                    dialog_manager.dialog_data["current_month"] = displayed_month_name
                    dialog_manager.dialog_data["current_year"] = displayed_year
        except Exception:
            pass

    # Переключаемся в текстовый вид
    await dialog_manager.switch_to(Schedules.my)

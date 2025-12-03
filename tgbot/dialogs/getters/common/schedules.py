"""Геттеры для функций графиков."""

import re
from datetime import datetime
from typing import Any, Dict

from aiogram import Bot
from aiogram_dialog import DialogManager
from stp_database.models.STP import Employee
from stp_database.repo.STP import MainRequestsRepo

from tgbot.misc.dicts import months_emojis, russian_months, schedule_types
from tgbot.services.files_processing.formatters.schedule import (
    get_current_date,
    get_current_month,
)
from tgbot.services.files_processing.handlers.schedule import schedule_service
from tgbot.services.files_processing.parsers.schedule import ScheduleParser


async def schedules_getter(
    user: Employee, stp_repo: MainRequestsRepo, **_kwargs
) -> Dict[str, Any]:
    """Геттер для главного меню графиков.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь с доступом сотрудника к бирже
    """
    is_banned = await stp_repo.exchange.is_user_exchange_banned(user.user_id)
    return {"is_banned": is_banned}


async def user_schedule_getter(
    bot: Bot,
    user: Employee,
    stp_repo: MainRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> Dict[str, Any]:
    """Геттер навигации по месяцам для расписания сотрудника.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь для смены месяца графика
    """
    current_month = dialog_manager.dialog_data.get("current_month", get_current_month())

    month_emoji = months_emojis.get(current_month.lower(), "📅")

    selected_mode = dialog_manager.find("schedule_mode").get_checked()
    is_detailed_mode = selected_mode == "detailed"
    button_text = "📋 Кратко" if is_detailed_mode else "📋 Подробнее"

    mode_options = [
        ("compact", "Кратко"),
        ("detailed", "Детально"),
    ]

    schedule_text = await schedule_service.get_user_schedule_response(
        user=user,
        month=current_month,
        compact=not is_detailed_mode,
        stp_repo=stp_repo,
        bot=bot,
    )

    return {
        "current_month": current_month,
        "month_emoji": month_emoji,
        "month_display": f"{month_emoji} {current_month.capitalize()}",
        "schedule_text": schedule_text,
        "detail_button_text": button_text,
        "is_detailed_mode": is_detailed_mode,
        "mode_options": mode_options,
        "selected_mode": selected_mode,
    }


async def duty_schedule_getter(
    user: Employee, stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для получения расписания дежурных.

    Стандартно возвращает расписание на текущий день

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с текстом графика дежурных
    """
    current_date_str = dialog_manager.dialog_data.get("current_date")
    if current_date_str is None:
        current_date = get_current_date()
    else:
        current_date = datetime.fromisoformat(current_date_str)

    duties_text = await schedule_service.get_duties_response(
        division=user.division, date=current_date, stp_repo=stp_repo
    )

    date_display = current_date.strftime("%d.%m")
    is_today = current_date.date() == get_current_date().date()

    return {
        "duties_text": duties_text,
        "date_display": date_display,
        "is_today": is_today,
    }


async def head_schedule_getter(
    user: Employee, stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для получения расписания руководителей.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с текстом графика руководителей
    """
    current_date_str = dialog_manager.dialog_data.get("current_date")
    if current_date_str is None:
        current_date = get_current_date()
    else:
        current_date = datetime.fromisoformat(current_date_str)

    heads_text = await schedule_service.get_heads_response(
        division=user.division, date=current_date, stp_repo=stp_repo
    )

    date_display = current_date.strftime("%d.%m")
    is_today = current_date.date() == get_current_date().date()

    return {
        "heads_text": heads_text,
        "date_display": date_display,
        "is_today": is_today,
    }


async def group_schedule_getter(
    user: Employee, stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для получения расписания группы сотрудника.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с текстом графика группы сотрудника
    """
    current_date_str = dialog_manager.dialog_data.get("current_date")
    if current_date_str is None:
        current_date = get_current_date()
    else:
        current_date = datetime.fromisoformat(current_date_str)

    (
        group_text,
        total_pages,
        has_prev,
        has_next,
    ) = await schedule_service.get_group_schedule_response(
        user=user,
        date=current_date,
        stp_repo=stp_repo,
        is_head=True if user.role == 2 else False,
    )

    date_display = current_date.strftime("%d.%m")
    is_today = current_date.date() == get_current_date().date()

    return {
        "group_text": group_text,
        "date_display": date_display,
        "is_today": is_today,
    }


async def prepare_schedule_calendar_data(
    stp_repo: MainRequestsRepo,
    user: Employee,
    dialog_manager: DialogManager,
    target_month: str = None,
) -> None:
    """Подготавливает данные календаря для отображения рабочих дней в графике.

    Args:
        stp_repo: Репозиторий операций с базой STP
        user: Пользователь
        dialog_manager: Менеджер диалога
        target_month: Целевой месяц для загрузки (если None, то текущий)
    """
    try:
        # Получаем календарный виджет
        calendar_widget = dialog_manager.find("my_schedule_calendar")

        # Определяем месяц для загрузки
        if target_month:
            month_name = target_month
        elif calendar_widget:
            current_offset = calendar_widget.get_offset()
            if current_offset:
                month_name = russian_months.get(
                    current_offset.month, get_current_month()
                )
            else:
                month_name = get_current_month()
        else:
            month_name = get_current_month()

        # Проверяем, не загружали ли мы уже данные для этого месяца
        # Если loaded_schedule_month пустой, значит нужно загрузить данные заново
        loaded_month = dialog_manager.dialog_data.get("loaded_schedule_month", "")
        if loaded_month and loaded_month == month_name:
            return

        # Очищаем предыдущие данные при смене месяца
        dialog_manager.dialog_data["shift_dates"] = {}

        # Загружаем данные расписания
        parser = ScheduleParser()
        all_shift_dates = {}
        current_date = datetime.now().date()

        try:
            # Получаем расписание с дежурствами (включает в себя базовое расписание)
            schedule_dict = await parser.get_user_schedule_with_duties(
                user.fullname,
                month_name,
                user.division,
                stp_repo,
                current_day_only=False,
            )

            if not schedule_dict:
                dialog_manager.dialog_data["shift_dates"] = {}
                dialog_manager.dialog_data["loaded_schedule_month"] = month_name
                return

            # Получаем номер месяца
            month_to_num = {name.lower(): num for num, name in russian_months.items()}
            month_num = month_to_num.get(month_name.lower())
            if not month_num:
                return

            # Извлекаем рабочие дни
            for day, (schedule, duty_info) in schedule_dict.items():
                if schedule and not any(
                    schedule in schedule_list
                    for schedule_list in schedule_types.values()
                ):
                    # Извлекаем номер дня
                    day_match = re.search(r"(\d{1,2})", day)
                    if day_match:
                        day_num = f"{int(day_match.group(1)):02d}"
                        # Создаем ключ для месяца и дня
                        month_day_key = f"{month_num:02d}_{day_num}"
                        all_shift_dates[month_day_key] = {
                            "schedule": schedule,
                            "duty_info": duty_info,
                            "month": month_num,
                            "day": int(day_num),
                            "year": current_date.year,
                        }

                        # Для текущего месяца сохраняем также простой ключ
                        if month_name.lower() == get_current_month().lower():
                            all_shift_dates[day_num] = {
                                "schedule": schedule,
                                "duty_info": duty_info,
                            }

        except Exception:
            all_shift_dates = {}

        # Сохраняем данные в dialog_data
        dialog_manager.dialog_data["shift_dates"] = all_shift_dates
        dialog_manager.dialog_data["loaded_schedule_month"] = month_name

    except Exception:
        dialog_manager.dialog_data["shift_dates"] = {}


async def my_schedule_calendar_getter(
    user: Employee, stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для календарного вида моего расписания.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с данными для календарного отображения
    """
    # Получаем отображаемый месяц из календаря
    calendar_widget = dialog_manager.find("my_schedule_calendar")
    displayed_month_name = get_current_month()

    if calendar_widget:
        try:
            current_offset = calendar_widget.get_offset()
            if current_offset:
                displayed_month_name = russian_months.get(
                    current_offset.month, get_current_month()
                )
        except Exception:
            pass

    # Подготавливаем данные календаря для отображения рабочих дней
    # Форсируем перезагрузку данных при каждом вызове геттера
    dialog_manager.dialog_data["loaded_schedule_month"] = ""
    await prepare_schedule_calendar_data(
        stp_repo, user, dialog_manager, displayed_month_name
    )

    month_emoji = months_emojis.get(displayed_month_name.lower(), "📅")

    return {
        "month": displayed_month_name.capitalize(),
        "month_emoji": month_emoji,
        "month_display": f"{month_emoji} {displayed_month_name.capitalize()}",
    }

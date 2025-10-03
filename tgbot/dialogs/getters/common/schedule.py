from datetime import datetime
from typing import Any, Dict

from aiogram_dialog import DialogManager

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.misc.dicts import months_emojis
from tgbot.services.schedule.schedule_handlers import schedule_service


async def user_schedule_getter(
    user: Employee, stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер навигации по месяцам для расписания сотрудника.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Возвращает словарь для смены месяца графика
    """
    # Get month from dialog_data or use current month as default
    current_month = dialog_manager.dialog_data.get(
        "current_month", schedule_service.get_current_month()
    )

    month_emoji = months_emojis.get(current_month.lower(), "📅")

    # Get mode from dialog_data, default to compact
    dialog_data = dialog_manager.dialog_data
    selected_mode = dialog_data.get("schedule_mode", "compact")
    is_detailed_mode = selected_mode == "detailed"
    button_text = "📋 Кратко" if is_detailed_mode else "📋 Подробнее"

    mode_options = [
        ("compact", "Кратко"),
        ("detailed", "Детально"),
    ]

    schedule_text = await schedule_service.get_user_schedule_response(
        user=user, month=current_month, compact=not is_detailed_mode, stp_repo=stp_repo
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
        current_date = schedule_service.get_current_date()
    else:
        current_date = datetime.fromisoformat(current_date_str)

    duties_text = await schedule_service.get_duties_response(
        division=user.division, date=current_date, stp_repo=stp_repo
    )

    date_display = current_date.strftime("%d.%m")
    is_today = current_date.date() == schedule_service.get_current_date().date()

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
        current_date = schedule_service.get_current_date()
    else:
        current_date = datetime.fromisoformat(current_date_str)

    heads_text = await schedule_service.get_heads_response(
        division=user.division, date=current_date, stp_repo=stp_repo
    )

    date_display = current_date.strftime("%d.%m")
    is_today = current_date.date() == schedule_service.get_current_date().date()

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
        current_date = schedule_service.get_current_date()
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
    is_today = current_date.date() == schedule_service.get_current_date().date()

    return {
        "group_text": group_text,
        "date_display": date_display,
        "is_today": is_today,
    }

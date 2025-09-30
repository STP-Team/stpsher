import datetime
from typing import cast

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.dialogs.getters.common.db import db_getter
from tgbot.services.schedule.schedule_handlers import schedule_service


async def schedule_getter(**kwargs):
    base_data = await db_getter(**kwargs)

    current_month = schedule_service.get_current_month()

    return {**base_data, "current_month": current_month}


async def user_schedule_getter(**kwargs):
    schedule_data = await schedule_getter(**kwargs)

    user = cast(Employee, cast(object, schedule_data.get("user")))
    stp_repo = cast(MainRequestsRepo, cast(object, schedule_data.get("stp_repo")))
    current_month = schedule_data.get("current_month")

    schedule_text = await schedule_service.get_user_schedule_response(
        user=user, month=current_month, compact=True, stp_repo=stp_repo
    )

    return {**schedule_data, "schedule_text": schedule_text}


async def duty_schedule_getter(**kwargs):
    base_data = await schedule_getter(**kwargs)

    dialog_manager = kwargs.get("dialog_manager")
    current_date_str = (
        dialog_manager.dialog_data.get("current_date") if dialog_manager else None
    )

    if current_date_str:
        current_date = datetime.datetime.fromisoformat(current_date_str)
    else:
        current_date = schedule_service.get_current_date()

    user = cast(Employee, cast(object, base_data.get("user")))
    stp_repo = cast(MainRequestsRepo, cast(object, base_data.get("stp_repo")))

    duties_text = await schedule_service.get_duties_response(
        division=user.division, date=current_date, stp_repo=stp_repo
    )

    # Format date for display
    date_display = current_date.strftime("%d.%m")
    is_today = current_date.date() == schedule_service.get_current_date().date()

    return {
        **base_data,
        "duties_text": duties_text,
        "date_display": date_display,
        "is_today": is_today,
    }


async def head_schedule_getter(**kwargs):
    base_data = await schedule_getter(**kwargs)

    dialog_manager = kwargs.get("dialog_manager")
    current_date_str = (
        dialog_manager.dialog_data.get("current_date") if dialog_manager else None
    )

    if current_date_str:
        current_date = datetime.datetime.fromisoformat(current_date_str)
    else:
        current_date = schedule_service.get_current_date()

    user = cast(Employee, cast(object, base_data.get("user")))
    stp_repo = cast(MainRequestsRepo, cast(object, base_data.get("stp_repo")))

    heads_text = await schedule_service.get_heads_response(
        division=user.division, date=current_date, stp_repo=stp_repo
    )

    # Format date for display
    date_display = current_date.strftime("%d.%m")
    is_today = current_date.date() == schedule_service.get_current_date().date()

    return {
        **base_data,
        "heads_text": heads_text,
        "date_display": date_display,
        "is_today": is_today,
    }


async def group_schedule_getter(**kwargs):
    base_data = await schedule_getter(**kwargs)

    dialog_manager = kwargs.get("dialog_manager")
    current_date_str = (
        dialog_manager.dialog_data.get("current_date") if dialog_manager else None
    )

    if current_date_str:
        current_date = datetime.datetime.fromisoformat(current_date_str)
    else:
        current_date = schedule_service.get_current_date()

    user = cast(Employee, cast(object, base_data.get("user")))
    stp_repo = cast(MainRequestsRepo, cast(object, base_data.get("stp_repo")))

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

    # Format date for display
    date_display = current_date.strftime("%d.%m")
    is_today = current_date.date() == schedule_service.get_current_date().date()

    return {
        **base_data,
        "group_text": group_text,
        "date_display": date_display,
        "is_today": is_today,
    }


async def month_navigation_getter(**kwargs):
    from tgbot.keyboards.common.schedule import MONTH_EMOJIS, get_yekaterinburg_date
    from tgbot.misc.states.dialogs.user import UserSG

    dialog_manager = kwargs.get("dialog_manager")
    current_month = dialog_manager.dialog_data.get("current_month")

    if not current_month:
        current_month_index = get_yekaterinburg_date().month - 1
        from tgbot.keyboards.common.schedule import MONTHS_RU

        current_month = MONTHS_RU[current_month_index]
        dialog_manager.dialog_data["current_month"] = current_month

    month_emoji = MONTH_EMOJIS.get(current_month.lower(), "📅")

    base_data = await db_getter(**kwargs)
    user: Employee = base_data.get("user")
    stp_repo: MainRequestsRepo = base_data.get("stp_repo")

    schedule_text = await schedule_service.get_user_schedule_response(
        user=user, month=current_month, compact=True, stp_repo=stp_repo
    )

    # Determine current mode for button text
    current_state = dialog_manager.current_context().state
    is_detailed_mode = current_state == UserSG.schedule_my_detailed
    button_text = "📋 Кратко" if is_detailed_mode else "📋 Подробнее"

    mode_options = [
        ("compact", "Кратко"),
        ("detailed", "Детально"),
    ]

    selected_mode = "detailed" if is_detailed_mode else "compact"

    return {
        **base_data,
        "current_month": current_month,
        "month_emoji": month_emoji,
        "month_display": f"{month_emoji} {current_month.capitalize()}",
        "schedule_text": schedule_text,
        "detail_button_text": button_text,
        "is_detailed_mode": is_detailed_mode,
        "mode_options": mode_options,
        "selected_mode": selected_mode,
    }


async def detailed_schedule_getter(**kwargs):
    schedule_data = await month_navigation_getter(**kwargs)

    user: Employee = schedule_data.get("user")
    stp_repo: MainRequestsRepo = schedule_data.get("stp_repo")
    current_month = schedule_data.get("current_month")

    schedule_text = await schedule_service.get_user_schedule_response(
        user=user, month=current_month, compact=False, stp_repo=stp_repo
    )

    return {**schedule_data, "schedule_text": schedule_text}

import re
from datetime import datetime
from typing import Any, Dict

from aiogram_dialog import DialogManager
from stp_database import Employee, MainRequestsRepo

from tgbot.dialogs.getters.common.exchanges.exchanges import (
    get_month_name,
    prepare_calendar_data_for_exchange,
)
from tgbot.services.files_processing.parsers.schedule import ScheduleParser


async def sell_date_getter(
    stp_repo: MainRequestsRepo, user: Employee, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна выбора даты."""
    # Подготавливаем данные календаря с информацией о сменах
    await prepare_calendar_data_for_exchange(stp_repo, user, dialog_manager)
    return {}


async def sell_hours_getter(
    stp_repo: MainRequestsRepo, user: Employee, dialog_manager: DialogManager, **kwargs
) -> Dict[str, Any]:
    """Геттер для окна выбора часов."""
    shift_date = dialog_manager.dialog_data.get("shift_date")
    is_today = dialog_manager.dialog_data.get("is_today", False)

    if not shift_date:
        return {
            "selected_date": "Не выбрана",
            "shift_options": [],
            "user_schedule": "Не найден",
        }

    try:
        # Получаем график пользователя с дежурствами
        date_obj = datetime.fromisoformat(shift_date).date()
        formatted_date = date_obj.strftime("%d.%m.%Y")

        parser = ScheduleParser()
        month_name = get_month_name(date_obj.month)

        # Получаем график с дежурствами
        try:
            schedule_with_duties = await parser.get_user_schedule_with_duties(
                user.fullname,
                month_name,
                user.division,
                stp_repo,
                current_day_only=False,
            )
        except Exception:
            schedule_with_duties = {}

        # Извлекаем информацию о смене на выбранную дату
        user_schedule = "Не указано"
        duty_warning = ""

        # Ищем данные на выбранную дату
        day_key = f"{date_obj.day:02d}"
        for day, (schedule, duty_info) in schedule_with_duties.items():
            if day_key in day:
                user_schedule = schedule or "Не указано"
                if duty_info:
                    duty_warning = (
                        f"⚠️ ВНИМАНИЕ: В это время у тебя дежурство ({duty_info})"
                    )
                break

        # Определяем доступные опции
        shift_options = []

        if user_schedule and user_schedule not in ["Не указано", "В", "О"]:
            # Проверяем, есть ли время в графике
            time_pattern = r"\d{1,2}:\d{2}-\d{1,2}:\d{2}"
            has_time = re.search(time_pattern, user_schedule)

            if has_time:
                shift_options.append(("full", "🕘 Полная смена"))
                shift_options.append(("partial", "⏰ Часть смены"))

                # Если это сегодня и смена уже началась, добавляем опцию "оставшееся время"
                if is_today:
                    current_time = datetime.now()
                    # Простая проверка - если сейчас после 9 утра, то смена могла начаться
                    if current_time.hour >= 9:
                        shift_options = [
                            ("remaining_today", "⏰ Оставшееся время сегодня")
                        ]
            else:
                # Если нет времени в графике, предлагаем ввести вручную
                shift_options.append(("partial", "⏰ Введите время смены"))
        else:
            # Если график не найден или сотрудник не работает
            user_schedule = "Нет смены / Выходной"

        return {
            "selected_date": formatted_date,
            "user_schedule": user_schedule,
            "duty_warning": duty_warning,
            "shift_options": shift_options,
        }

    except Exception as e:
        date_obj = datetime.fromisoformat(shift_date).date()
        formatted_date = date_obj.strftime("%d.%m.%Y")
        return {
            "selected_date": formatted_date,
            "user_schedule": f"Ошибка: {str(e)}",
            "duty_warning": "",
            "shift_options": [],
        }


async def sell_time_input_getter(
    stp_repo: MainRequestsRepo, user: Employee, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна ввода времени."""
    shift_date = dialog_manager.dialog_data.get("shift_date")

    if not shift_date:
        return {"selected_date": "Не выбрана", "user_schedule": "Не найден"}

    try:
        date_obj = datetime.fromisoformat(shift_date).date()
        formatted_date = date_obj.strftime("%d.%m.%Y")

        parser = ScheduleParser()
        month_name = get_month_name(date_obj.month)

        # Получаем график пользователя
        user_schedule = "Не указано"
        duty_warning = ""

        try:
            schedule_dict = await parser.get_user_schedule_with_duties(
                user.fullname,
                month_name,
                user.division,
                stp_repo,
                current_day_only=False,
            )

            day_key = f"{date_obj.day:02d}"
            for day, (schedule, duty_info) in schedule_dict.items():
                if day_key in day:
                    user_schedule = schedule or "Не указано"
                    if duty_info:
                        duty_warning = (
                            f"⚠️ ВНИМАНИЕ: Проверьте время дежурства ({duty_info})"
                        )
                    break
        except Exception:
            pass

        return {
            "selected_date": formatted_date,
            "user_schedule": user_schedule,
            "duty_warning": duty_warning,
        }

    except Exception:
        date_obj = datetime.fromisoformat(shift_date).date()
        formatted_date = date_obj.strftime("%d.%m.%Y")
        return {
            "selected_date": formatted_date,
            "user_schedule": "Ошибка получения графика",
            "duty_warning": "",
        }


async def sell_price_getter(dialog_manager: DialogManager, **_kwargs) -> Dict[str, Any]:
    """Геттер для окна ввода цены."""
    shift_date = dialog_manager.dialog_data.get("shift_date")
    start_time = dialog_manager.dialog_data.get("start_time")
    end_time = dialog_manager.dialog_data.get("end_time")

    shift_type = "часть смены" if end_time else "полную смену"
    shift_time = ""

    if start_time:
        if end_time:
            # Извлекаем только время из datetime строк
            start_time_str = (
                start_time.split("T")[1][:5] if "T" in start_time else start_time
            )
            end_time_str = end_time.split("T")[1][:5] if "T" in end_time else end_time
            shift_time = f"{start_time_str}-{end_time_str}"
        else:
            start_time_str = (
                start_time.split("T")[1][:5] if "T" in start_time else start_time
            )
            shift_time = f"с {start_time_str}"

    if shift_date:
        date_obj = datetime.fromisoformat(shift_date).date()
        formatted_date = date_obj.strftime("%d.%m.%Y")
        return {
            "selected_date": formatted_date,
            "shift_type": shift_type,
            "shift_time": shift_time if shift_time else None,
        }
    return {
        "selected_date": "Не выбрана",
        "shift_type": shift_type,
        "shift_time": shift_time if shift_time else None,
    }


async def sell_payment_timing_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна выбора времени оплаты."""
    data = dialog_manager.dialog_data
    shift_date = data.get("shift_date")
    price = data.get("price", 0)
    end_time = data.get("end_time")
    shift_type = "часть смены" if end_time else "полную смену"

    if shift_date:
        date_obj = datetime.fromisoformat(shift_date).date()
        formatted_date = date_obj.strftime("%d.%m.%Y")
        return {
            "selected_date": formatted_date,
            "shift_type": shift_type,
            "price": price,
        }
    return {
        "selected_date": "Не выбрана",
        "shift_type": shift_type,
        "price": price,
    }


async def sell_payment_date_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна выбора даты платежа."""
    data = dialog_manager.dialog_data
    shift_date = data.get("shift_date")

    if shift_date:
        date_obj = datetime.fromisoformat(shift_date).date()
        formatted_date = date_obj.strftime("%d.%m.%Y")
        return {"shift_date": formatted_date}
    return {"shift_date": "Не выбрана"}


async def sell_comment_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна ввода комментария."""
    data = dialog_manager.dialog_data
    shift_date = data.get("shift_date")
    price = data.get("price", 0)
    end_time = data.get("end_time")

    shift_type = "часть смены" if end_time else "полную смену"

    if shift_date:
        date_obj = datetime.fromisoformat(shift_date).date()
        formatted_date = date_obj.strftime("%d.%m.%Y")
        return {
            "selected_date": formatted_date,
            "shift_type": shift_type,
            "price": price,
        }
    return {
        "selected_date": "Не выбрана",
        "shift_type": shift_type,
        "price": price,
    }


async def sell_confirmation_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна подтверждения."""
    data = dialog_manager.dialog_data

    # Базовые данные
    shift_date = data.get("shift_date")
    price = data.get("price", 0)
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    payment_type = data.get("payment_type", "immediate")
    payment_date = data.get("payment_date")
    comment = data.get("comment")

    # Форматируем дату смены
    formatted_shift_date = "Не выбрана"
    if shift_date:
        date_obj = datetime.fromisoformat(shift_date).date()
        formatted_shift_date = date_obj.strftime("%d.%m.%Y")

    # Тип смены
    shift_type = "Часть смены" if end_time else "Полная смена"

    # Время смены
    shift_time_info = ""
    if start_time:
        start_time_str = (
            start_time.split("T")[1][:5] if "T" in start_time else start_time
        )
        end_time_str = end_time.split("T")[1][:5] if "T" in end_time else end_time
        shift_time_info = f"{start_time_str}-{end_time_str}"

    # Информация об оплате
    payment_info = "Сразу при покупке"
    if payment_type == "on_date" and payment_date:
        payment_date_obj = datetime.fromisoformat(payment_date).date()
        formatted_payment_date = payment_date_obj.strftime("%d.%m.%Y")
        payment_info = f"До {formatted_payment_date}"

    result = {
        "shift_date": formatted_shift_date,
        "shift_type": shift_type,
        "shift_time": shift_time_info,
        "price": price,
        "payment_info": payment_info,
    }

    # Добавляем комментарий если есть
    if comment:
        result["comment"] = comment

    return result

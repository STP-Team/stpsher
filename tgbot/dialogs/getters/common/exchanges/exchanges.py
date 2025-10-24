"""Геттеры для биржи подмен."""

import re
from datetime import datetime
from typing import Any, Dict

from aiogram_dialog import DialogManager
from stp_database import Employee, MainRequestsRepo

from tgbot.misc.helpers import format_fullname
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
                        f"⚠️ ВНИМАНИЕ: В это время у вас дежурство ({duty_info})"
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
    is_partial = dialog_manager.dialog_data.get("is_partial", False)
    shift_start_time = dialog_manager.dialog_data.get("shift_start_time")
    shift_end_time = dialog_manager.dialog_data.get("shift_end_time")

    shift_type = "часть смены" if is_partial else "полную смену"
    shift_time = ""

    if is_partial and shift_start_time:
        if shift_end_time:
            shift_time = f"{shift_start_time}-{shift_end_time}"
        else:
            shift_time = f"с {shift_start_time}"

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
    is_partial = data.get("is_partial", False)
    shift_type = "часть смены" if is_partial else "полную смену"

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
    is_partial = data.get("is_partial", False)

    shift_type = "часть смены" if is_partial else "полную смену"

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
    is_partial = data.get("is_partial", False)
    payment_type = data.get("payment_type", "immediate")
    payment_date = data.get("payment_date")
    comment = data.get("comment")

    # Форматируем дату смены
    formatted_shift_date = "Не выбрана"
    if shift_date:
        date_obj = datetime.fromisoformat(shift_date).date()
        formatted_shift_date = date_obj.strftime("%d.%m.%Y")

    # Тип смены
    shift_type = "Часть смены" if is_partial else "Полная смена"

    # Время смены
    shift_start = data.get("shift_start_time")
    shift_end = data.get("shift_end_time")
    shift_time_info = f"с {shift_start} до {shift_end}"
    if is_partial and data.get("shift_end_time"):
        shift_time_info = f"{shift_start}-{data.get('shift_end_time')}"

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


def get_month_name(month_number: int) -> str:
    """Получить название месяца на русском языке."""
    months = [
        "",
        "Январь",
        "Февраль",
        "Март",
        "Апрель",
        "Май",
        "Июнь",
        "Июль",
        "Август",
        "Сентябрь",
        "Октябрь",
        "Ноябрь",
        "Декабрь",
    ]
    return months[month_number] if 1 <= month_number <= 12 else "Неизвестно"


async def prepare_calendar_data_for_exchange(
    stp_repo: MainRequestsRepo, user: Employee, dialog_manager: DialogManager
) -> None:
    """Подготавливает данные календаря с информацией о сменах пользователя."""
    try:
        # Получаем текущий месяц для календаря
        current_date = datetime.now().date()

        parser = ScheduleParser()
        month_name = get_month_name(current_date.month)

        # Получаем график пользователя на текущий месяц
        try:
            schedule_dict = await parser.get_user_schedule_with_duties(
                user.fullname,
                month_name,
                user.division,
                stp_repo,
                current_day_only=False,
            )

            # Извлекаем дни когда есть смены
            shift_dates = {}
            for day, (schedule, duty_info) in schedule_dict.items():
                if schedule and schedule not in ["Не указано", "В", "О"]:
                    # Извлекаем номер дня
                    day_match = re.search(r"(\d{1,2})", day)
                    if day_match:
                        day_num = f"{int(day_match.group(1)):02d}"
                        shift_dates[day_num] = {
                            "schedule": schedule,
                            "duty_info": duty_info,
                        }

            # Сохраняем данные в dialog_data для использования в календаре
            dialog_manager.dialog_data["shift_dates"] = shift_dates

            # Определяем пол пользователя для правильного эмодзи
            gender = determine_user_gender(user.fullname)
            dialog_manager.dialog_data["user_gender"] = gender

        except Exception:
            # В случае ошибки просто не показываем смены
            dialog_manager.dialog_data["shift_dates"] = {}

    except Exception:
        # В случае ошибки просто не показываем смены
        dialog_manager.dialog_data["shift_dates"] = {}


def determine_user_gender(fullname: str) -> str:
    """Определяет пол пользователя на основе имени."""
    if not fullname:
        return "unknown"

    # Простая эвристика на основе окончаний имен
    name_parts = fullname.split()
    if len(name_parts) >= 2:
        first_name = name_parts[1].lower()  # Второе слово обычно имя

        # Мужские окончания
        male_endings = ["ич", "ев", "ов", "ин", "ан", "ён", "он", "ий", "ей", "ай"]
        # Женские окончания
        female_endings = [
            "на",
            "ра",
            "ла",
            "да",
            "га",
            "ка",
            "са",
            "та",
            "ва",
            "ья",
            "ия",
            "ая",
        ]

        for ending in female_endings:
            if first_name.endswith(ending):
                return "female"

        for ending in male_endings:
            if first_name.endswith(ending):
                return "male"

    return "unknown"


async def exchange_buy_getter(
    stp_repo: MainRequestsRepo, user: Employee, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна покупки обменов."""
    user_id = dialog_manager.event.from_user.id

    try:
        # Получаем доступные обмены
        exchanges = await stp_repo.exchange.get_active_exchanges(
            exclude_user_id=user_id,
            division="НЦК" if user.division == "НЦК" else ["НТП1", "НТП2"],
        )

        # Форматируем данные для отображения
        available_exchanges = []
        for exchange in exchanges:
            # Форматируем время
            time_str = f"{exchange.shift_start_time}-{exchange.shift_end_time}"

            # Форматируем дату
            date_str = exchange.shift_date.strftime("%d.%m.%Y")

            available_exchanges.append({
                "id": exchange.id,
                "time": time_str,
                "date": date_str,
                "price": exchange.price,
                "seller_id": exchange.seller_id,
            })

        return {
            "available_exchanges": available_exchanges,
            "exchanges_length": len(available_exchanges),
            "has_exchanges": len(available_exchanges) > 0,
        }

    except Exception:
        return {
            "available_exchanges": [],
            "has_exchanges": False,
        }


async def exchange_sell_getter(
    stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна продажи обменов."""
    user_id = dialog_manager.event.from_user.id

    try:
        # Получаем активные обмены пользователя
        user_exchanges_data = await stp_repo.exchange.get_user_exchanges(
            user_id=user_id, status="active"
        )

        # Форматируем данные для отображения
        user_exchanges = []
        for exchange in user_exchanges_data:
            # Форматируем время
            time_str = f"{exchange.shift_start_time}-{exchange.shift_end_time}"

            # Форматируем дату
            date_str = exchange.shift_date.strftime("%d.%m.%Y")

            user_exchanges.append({
                "id": exchange.id,
                "time": time_str,
                "date": date_str,
                "price": exchange.price,
            })

        return {
            "user_exchanges": user_exchanges,
            "has_user_exchanges": len(user_exchanges) > 0,
        }

    except Exception:
        return {
            "user_exchanges": [],
            "has_user_exchanges": False,
        }


async def exchange_buy_detail_getter(
    stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **kwargs
) -> Dict[str, Any]:
    """Геттер для детального просмотра обмена при покупке."""
    if dialog_manager.start_data:
        exchange_id = dialog_manager.start_data.get("exchange_id", None)
    else:
        exchange_id = dialog_manager.dialog_data.get("exchange_id", None)

    if not exchange_id:
        return {"error": "Обмен не найден"}

    try:
        # Получаем детали обмена
        exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
        if not exchange:
            return {"error": "Обмен не найден"}

        # Получаем информацию о продавце
        seller = await stp_repo.employee.get_users(user_id=exchange.seller_id)
        seller_name = format_fullname(
            seller.fullname,
            short=True,
            gender_emoji=True,
            username=seller.username,
            user_id=seller.user_id,
        )

        # Форматируем данные
        shift_date = exchange.shift_date.strftime("%d.%m.%Y")

        shift_time = f"{exchange.shift_start_time}-{exchange.shift_end_time}"

        # Информация об оплате
        if exchange.payment_type == "immediate":
            payment_info = "Сразу при покупке"
        elif exchange.payment_date:
            payment_info = f"До {exchange.payment_date.strftime('%d.%m.%Y')}"
        else:
            payment_info = "По договоренности"

        deeplink = f"exchange_{exchange.id}"

        return {
            "shift_date": shift_date,
            "seller_name": seller_name,
            "shift_time": shift_time,
            "price": exchange.price,
            "payment_info": payment_info,
            "deeplink": deeplink,
        }

    except Exception:
        return {"error": "Ошибка загрузки данных"}


async def exchange_sell_detail_getter(
    stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **kwargs
) -> Dict[str, Any]:
    """Геттер для детального просмотра собственного обмена."""
    if dialog_manager.start_data:
        exchange_id = dialog_manager.start_data.get("exchange_id", None)
    else:
        exchange_id = dialog_manager.dialog_data.get("exchange_id", None)

    if not exchange_id:
        return {"error": "Обмен не найден"}

    try:
        # Получаем детали обмена
        exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
        if not exchange:
            return {"error": "Обмен не найден"}

        await dialog_manager.find("private_toggle").set_checked(exchange.is_private)

        # Форматируем данные
        shift_date = exchange.shift_date.strftime("%d.%m.%Y")

        if exchange.is_partial and exchange.shift_end_time:
            shift_type = "Часть смены"
            shift_time = f"с {exchange.shift_start_time} до {exchange.shift_end_time}"
        else:
            shift_type = "Полная смена"
            shift_time = f"с {exchange.shift_start_time} до {exchange.shift_end_time}"

        # Информация об оплате
        if exchange.payment_type == "immediate":
            payment_info = "Сразу при покупке"
        elif exchange.payment_date:
            payment_info = f"До {exchange.payment_date.strftime('%d.%m.%Y')}"
        else:
            payment_info = "По договоренности"

        # Статус обмена
        status_map = {
            "active": "🟢 Активно",
            "sold": "✅ Продано",
            "cancelled": "❌ Отменено",
            "expired": "⏰ Истекло",
        }
        status_text = status_map.get(exchange.status, "❓ Неизвестно")

        # Дата создания
        created_at = exchange.created_at.strftime("%d.%m.%Y %H:%M")

        deeplink = f"exchange_{exchange.id}"

        return {
            "shift_date": shift_date,
            "shift_type": shift_type,
            "shift_time": shift_time,
            "price": exchange.price,
            "payment_info": payment_info,
            "deeplink": deeplink,
            "status": exchange.status,
            "status_text": status_text,
            "created_at": created_at,
            "private": exchange.is_private,
        }

    except Exception:
        return {"error": "Ошибка загрузки данных"}

"""Геттеры для диалога продаж на бирже."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from aiogram import Bot
from aiogram.utils.deep_linking import create_start_link
from aiogram_dialog import DialogManager
from stp_database import Employee, MainRequestsRepo

from tgbot.dialogs.getters.common.exchanges.exchanges import (
    get_exchange_shift_time,
    prepare_calendar_data_for_exchange,
)

logger = logging.getLogger(__name__)


async def sell_date_getter(
    stp_repo: MainRequestsRepo, user: Employee, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна выбора даты."""
    # Подготавливаем данные календаря с информацией о сменах
    await prepare_calendar_data_for_exchange(stp_repo, user, dialog_manager)
    return {}


async def sell_hours_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    """Геттер для окна выбора часов."""
    data = dialog_manager.dialog_data

    shift_date = data.get("shift_date")
    shift_start = data.get("shift_start")
    shift_end = data.get("shift_end")
    has_duty = data.get("has_duty", False)
    duty_time = data.get("duty_time")
    duty_type = data.get("duty_type")
    is_remaining_today = data.get("is_remaining_today", False)

    if not shift_date or not shift_start or not shift_end:
        return {
            "selected_date": "Не выбрана",
            "shift_options": [],
            "user_schedule": "Не найден",
            "duty_warning": "",
        }

    try:
        date_obj = datetime.fromisoformat(shift_date).date()
        formatted_date = date_obj.strftime("%d.%m.%Y")
        user_schedule = f"{shift_start}-{shift_end}"

        # Формируем предупреждение о дежурстве
        duty_warning = ""
        if has_duty and duty_time and duty_type:
            duty_warning = f"🚩 Есть дежурство: {duty_time} {duty_type}"
        elif has_duty:
            # Fallback если по какой-то причине нет детальной информации
            duty_warning = "🚩 Есть дежурство"

        if is_remaining_today:
            # Если это оставшееся время сегодня, показываем только эту опцию
            shift_options = [("remaining_today", "⏰ Оставшееся время сегодня")]
        else:
            # Обычные опции для будущих дат или сегодня до начала смены
            shift_options = [
                ("full", "🕘 Полная смена"),
                ("partial", "⏰ Часть смены"),
            ]

        return {
            "selected_date": formatted_date,
            "user_schedule": user_schedule,
            "duty_warning": duty_warning,
            "shift_options": shift_options,
        }

    except Exception as e:
        logger.error(f"[Биржа] Ошибка в sell_hours_getter: {e}")
        return {
            "selected_date": "Ошибка",
            "user_schedule": "Ошибка получения данных",
            "duty_warning": "",
            "shift_options": [],
        }


async def sell_time_input_getter(
    dialog_manager: DialogManager, bot: Bot, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна ввода времени."""
    data = dialog_manager.dialog_data

    shift_date = data.get("shift_date")
    shift_start = data.get("shift_start")
    shift_end = data.get("shift_end")
    has_duty = data.get("has_duty", False)
    duty_time = data.get("duty_time")
    duty_type = data.get("duty_type")
    sold_time_strings = data.get("sold_time_strings", [])
    is_today = data.get("is_today", False)

    if not shift_date or not shift_start or not shift_end:
        return {
            "selected_date": "Не выбрана",
            "user_schedule": "Не найден",
            "duty_warning": "",
            "sold_hours_info": "",
            "show_remaining_time_button": False,
        }

    try:
        date_obj = datetime.fromisoformat(shift_date).date()
        formatted_date = date_obj.strftime("%d.%m.%Y")
        user_schedule = f"{shift_start}-{shift_end}"

        # Формируем предупреждение о дежурстве
        duty_warning = ""
        if has_duty:
            duty_warning = f"\n🚩 <b>Есть дежурство:</b>\n{duty_time} {duty_type}"

        # Формируем информацию о проданных часах
        sold_hours_info = ""
        if sold_time_strings:
            sold_hours_list = []
            for exchange_data in sold_time_strings:
                # exchange_data содержит time_str, exchange_id, status
                time_str = exchange_data.get("time_str", "")
                exchange_id = exchange_data.get("exchange_id", "")
                status = exchange_data.get("status", "продается")

                # Создаем ссылку
                exchange_deeplink = f"exchange_{exchange_id}"
                exchange_link = await create_start_link(
                    bot=bot, payload=exchange_deeplink, encode=True
                )

                # Формируем строку со ссылкой и статусом
                sold_hours_list.append(
                    f"• <a href='{exchange_link}'>{time_str}</a> - {status}"
                )

            sold_hours_info = "\n🚩 <b>Есть сделки:</b>\n" + "\n".join(sold_hours_list)

        # Проверяем, осталось ли минимум 30 минут от ближайшего получасового интервала до конца смены
        show_remaining_time_button = False
        if is_today:
            try:
                # Парсим время окончания смены
                shift_end_time = datetime.strptime(shift_end, "%H:%M").time()

                # Получаем текущее время и вычисляем ближайший получасовой интервал
                current_datetime = datetime.now()
                current_time = current_datetime.time()

                # Вычисляем следующий доступный получасовой интервал (:00 или :30)
                if current_time.minute < 30:
                    # Округляем ВВЕРХ к :30 текущего часа
                    next_slot_start = current_datetime.replace(
                        minute=30, second=0, microsecond=0
                    )
                else:
                    # Округляем ВВЕРХ к :00 следующего часа
                    next_slot_start = current_datetime.replace(
                        minute=0, second=0, microsecond=0
                    ) + timedelta(hours=1)

                # Создаем datetime объект для времени окончания смены
                today = datetime.now().date()
                shift_end_datetime = datetime.combine(today, shift_end_time)

                # Находим ближайший валидный получасовой интервал ДО времени окончания смены
                # Время окончания также должно быть на границе :00 или :30
                if shift_end_time.minute == 0:
                    # Если смена заканчивается ровно в час, используем это время
                    valid_end_datetime = shift_end_datetime
                elif shift_end_time.minute == 30:
                    # Если смена заканчивается в полчаса, используем это время
                    valid_end_datetime = shift_end_datetime
                elif shift_end_time.minute < 30:
                    # Округляем вниз к :00 текущего часа
                    valid_end_datetime = shift_end_datetime.replace(
                        minute=0, second=0, microsecond=0
                    )
                else:
                    # Округляем вниз к :30 текущего часа
                    valid_end_datetime = shift_end_datetime.replace(
                        minute=30, second=0, microsecond=0
                    )

                # Проверяем, что от ближайшего получасового интервала до валидного времени окончания минимум 30 минут
                time_remaining = valid_end_datetime - next_slot_start
                show_remaining_time_button = time_remaining >= timedelta(minutes=30)

            except Exception as e:
                logger.error(f"[Биржа] Ошибка при проверке оставшегося времени: {e}")
                show_remaining_time_button = False

        return {
            "selected_date": formatted_date,
            "user_schedule": user_schedule,
            "duty_warning": duty_warning,
            "sold_hours_info": sold_hours_info,
            "show_remaining_time_button": show_remaining_time_button,
        }

    except Exception as e:
        logger.error(f"[Биржа] Ошибка в sell_time_input_getter: {e}")
        return {
            "selected_date": "Ошибка",
            "user_schedule": "Ошибка получения данных",
            "duty_warning": "",
            "sold_hours_info": "",
            "show_remaining_time_button": False,
        }


async def sell_price_getter(dialog_manager: DialogManager, **_kwargs) -> Dict[str, Any]:
    """Геттер для окна ввода цены."""
    data = dialog_manager.dialog_data

    shift_date = data.get("shift_date")
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    shift_time = await get_exchange_shift_time(start_time, end_time)

    if shift_date:
        date_obj = datetime.fromisoformat(shift_date).date()
        formatted_date = date_obj.strftime("%d.%m.%Y")
        return {
            "selected_date": formatted_date,
            "shift_date": shift_date,
            "shift_time": shift_time,
        }
    return {
        "selected_date": "Не выбрана",
        "shift_date": shift_date,
        "shift_time": shift_time,
    }


async def sell_payment_timing_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна выбора времени оплаты."""
    data = dialog_manager.dialog_data

    shift_date = data.get("shift_date")
    price = data.get("price", 0)
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    shift_time = await get_exchange_shift_time(start_time, end_time)

    if shift_date:
        date_obj = datetime.fromisoformat(shift_date).date()
        formatted_date = date_obj.strftime("%d.%m.%Y")
        return {
            "selected_date": formatted_date,
            "shift_date": shift_date,
            "shift_time": shift_time,
            "price": price,
        }
    return {
        "selected_date": "Не выбрана",
        "shift_date": shift_date,
        "shift_time": shift_time,
        "price": price,
    }


async def sell_payment_date_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна выбора даты платежа."""
    data = dialog_manager.dialog_data

    shift_date = data.get("shift_date")
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    price = data.get("price")

    shift_time = await get_exchange_shift_time(start_time, end_time)

    if shift_date:
        date_obj = datetime.fromisoformat(shift_date).date()
        formatted_date = date_obj.strftime("%d.%m.%Y")
        return {"shift_date": formatted_date, "shift_time": shift_time, "price": price}
    return {"shift_date": "Не выбрана"}


async def sell_comment_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна ввода комментария."""
    data = dialog_manager.dialog_data

    shift_date = data.get("shift_date")
    price = data.get("price", 0)
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    payment_type = data.get("payment_type")

    shift_time = await get_exchange_shift_time(start_time, end_time)

    if shift_date:
        date_obj = datetime.fromisoformat(shift_date).date()
        formatted_date = date_obj.strftime("%d.%m.%Y")
        return {
            "selected_date": formatted_date,
            "shift_date": shift_date,
            "shift_time": shift_time,
            "price": price,
            "payment_type": "Сразу"
            if payment_type == "immediate"
            else "В выбранную дату",
        }
    return {
        "selected_date": "Не выбрана",
        "shift_date": shift_date,
        "shift_time": shift_time,
        "price": price,
        "payment_type": "Сразу" if payment_type == "immediate" else "В выбранную дату",
    }


async def sell_confirmation_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна подтверждения."""
    data = dialog_manager.dialog_data

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
        "shift_time": shift_time_info,
        "price": price,
        "payment_info": payment_info,
    }

    # Добавляем комментарий если есть
    if comment:
        result["comment"] = comment

    return result

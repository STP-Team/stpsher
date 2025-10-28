"""Обработчики для диалога создания продажи на бирже."""

import logging
import re
from datetime import datetime
from typing import Any, Optional, Tuple

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import ChatEvent, DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.kbd import Button, ManagedCalendar, Select
from stp_database import MainRequestsRepo

from tgbot.dialogs.getters.common.exchanges.exchanges import get_exchange_status
from tgbot.dialogs.states.common.exchanges import (
    ExchangeCreateSell,
    Exchanges,
)
from tgbot.misc.helpers import tz
from tgbot.services.files_processing.parsers.schedule import (
    DutyScheduleParser,
    ScheduleParser,
)

logger = logging.getLogger(__name__)


async def get_user_shift_info(
    dialog_manager: DialogManager,
    shift_date: str,
) -> Optional[Tuple[str, str, bool]]:
    """Получает информацию о смене пользователя на выбранную дату.

    Args:
        dialog_manager: Менеджер диалога
        shift_date: Дата смены в формате ISO

    Returns:
        Кортеж (start_time, end_time, has_duty) или None если смена не найдена
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user_id = dialog_manager.event.from_user.id

    try:
        # Получаем пользователя
        employee = await stp_repo.employee.get_users(user_id=user_id)
        if not employee:
            return None

        # Получаем график пользователя
        date_obj = datetime.fromisoformat(shift_date).date()
        parser = ScheduleParser()

        def get_month_name(month_number: int) -> str:
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

        month_name = get_month_name(date_obj.month)

        # Получаем базовый график без дежурств
        schedule_data = parser.get_user_schedule(
            employee.fullname, month_name, employee.division
        )

        # Ищем смену на выбранную дату
        day_key = f"{date_obj.day:02d}"
        shift_start = None
        shift_end = None

        for day, schedule in schedule_data.items():
            if day_key in day and schedule:
                # Проверяем, есть ли время в графике
                time_pattern = r"(\d{1,2}:\d{2})-(\d{1,2}:\d{2})"
                match = re.search(time_pattern, schedule)
                if match:
                    shift_start = match.group(1)
                    shift_end = match.group(2)
                    break

        if not shift_start or not shift_end:
            return None

        # Проверяем реальные дежурства напрямую через DutyScheduleParser
        has_actual_duty = False
        try:
            duty_parser = DutyScheduleParser()
            duties_for_date = await duty_parser.get_duties_for_date(
                date_obj, employee.division, stp_repo
            )

            if duties_for_date:
                # Проверяем, есть ли пользователь среди дежурных
                for duty in duties_for_date:
                    if duty_parser.names_match(employee.fullname, duty.name):
                        has_actual_duty = True
                        break
        except Exception as e:
            logger.debug(f"[Биржа] Ошибка проверки дежурств: {e}")
            has_actual_duty = False

        return shift_start, shift_end, has_actual_duty

    except Exception as e:
        logger.error(f"[Биржа] Ошибка получения смены: {e}")
        return None


async def check_existing_exchanges_overlap(
    dialog_manager: DialogManager,
    start_time: datetime,
    end_time: datetime,
) -> bool:
    """Проверяет, есть ли пересекающиеся активные обмены у пользователя.

    Args:
        dialog_manager: Менеджер диалога
        start_time: Время начала предполагаемого обмена
        end_time: Время окончания предполагаемого обмена

    Returns:
        True если есть пересечение, False если нет
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user_id = dialog_manager.event.from_user.id

    try:
        # Получаем активные обмены пользователя
        user_exchanges = await stp_repo.exchange.get_user_exchanges(
            user_id=user_id, status="active"
        )

        for exchange in user_exchanges:
            # Проверяем пересечение временных интервалов
            if start_time < exchange.end_time and end_time > exchange.start_time:
                return True

        return False

    except Exception as e:
        logger.error(f"[Биржа] Ошибка проверки пересечений: {e}")
        return False


async def get_existing_sales_for_date(
    dialog_manager: DialogManager,
    shift_date: str,
    shift_start: str,
    shift_end: str,
) -> tuple[bool, list[tuple[str, str]], list[str]]:
    """Получает информацию о существующих продажах на указанную дату.

    Args:
        dialog_manager: Менеджер диалога
        shift_date: Дата смены в формате ISO
        shift_start: Время начала смены (HH:MM)
        shift_end: Время окончания смены (HH:MM)

    Returns:
        Кортеж (is_full_shift_sold, sold_time_ranges, sold_time_strings)
        - is_full_shift_sold: True если вся смена уже продана/продается
        - sold_time_ranges: Список кортежей (start, end) проданного времени
        - sold_time_strings: Список словарей с данными о проданных сделках
          {"time_str": "HH:MM-HH:MM", "exchange_id": int, "status": str}
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user_id = dialog_manager.event.from_user.id

    try:
        # Получаем активные и проданные обмены пользователя только как продавец
        user_exchanges = await stp_repo.exchange.get_user_exchanges(
            user_id=user_id, exchange_type="sold"
        )

        # Фильтруем только активные и проданные обмены
        relevant_exchanges = [
            exchange
            for exchange in user_exchanges
            if exchange.status in ["active", "sold"]
            and exchange.start_time
            and exchange.end_time
        ]

        # Фильтруем по дате
        shift_date_obj = datetime.fromisoformat(shift_date).date()
        date_exchanges = [
            exchange
            for exchange in relevant_exchanges
            if exchange.start_time.date() == shift_date_obj
        ]

        if not date_exchanges:
            return False, [], []

        # Получаем временные диапазоны проданного времени
        sold_time_ranges = []
        sold_time_strings = []

        for exchange in date_exchanges:
            start_str = exchange.start_time.strftime("%H:%M")
            end_str = exchange.end_time.strftime("%H:%M")
            sold_time_ranges.append((start_str, end_str))

            # Добавляем статус для отображения
            status_text = await get_exchange_status(exchange)
            sold_time_strings.append({
                "time_str": f"{start_str}-{end_str}",
                "exchange_id": exchange.id,
                "status": status_text,
            })

        # Проверяем, покрывают ли проданные части всю смену
        shift_start_minutes = time_to_minutes(shift_start)
        shift_end_minutes = time_to_minutes(shift_end)

        # Сортируем интервалы по времени начала
        sorted_ranges = sorted([
            (time_to_minutes(start), time_to_minutes(end))
            for start, end in sold_time_ranges
        ])

        # Проверяем покрытие всей смены
        is_full_shift_sold = False
        if sorted_ranges:
            # Объединяем пересекающиеся интервалы
            merged_ranges = [sorted_ranges[0]]
            for current_start, current_end in sorted_ranges[1:]:
                last_start, last_end = merged_ranges[-1]
                if current_start <= last_end:
                    # Интервалы пересекаются или соприкасаются
                    merged_ranges[-1] = (last_start, max(last_end, current_end))
                else:
                    merged_ranges.append((current_start, current_end))

            # Проверяем, покрывает ли объединенный интервал всю смену
            if (
                len(merged_ranges) == 1
                and merged_ranges[0][0] <= shift_start_minutes
                and merged_ranges[0][1] >= shift_end_minutes
            ):
                is_full_shift_sold = True

        return is_full_shift_sold, sold_time_ranges, sold_time_strings

    except Exception as e:
        logger.error(f"[Биржа] Ошибка получения информации о продажах: {e}")
        return False, [], []


def time_to_minutes(time_str: str) -> int:
    """Преобразует время в формате HH:MM в минуты от начала дня."""
    try:
        h, m = map(int, time_str.split(":"))
        return h * 60 + m
    except Exception:
        return 0


def is_shift_started(shift_start_time: str, shift_date: str) -> bool:
    """Проверяет, началась ли смена на указанную дату.

    Args:
        shift_start_time: Время начала смены в формате HH:MM
        shift_date: Дата смены в формате ISO

    Returns:
        True если смена началась, False если нет
    """
    try:
        current_time = datetime.now(tz=tz)
        shift_date_obj = datetime.fromisoformat(shift_date).date()

        # Если дата не сегодня, то смена не может быть начата
        if shift_date_obj != current_time.date():
            return False

        # Создаем datetime для времени начала смены
        shift_start = datetime.combine(
            shift_date_obj, datetime.strptime(shift_start_time, "%H:%M").time()
        )

        # Добавляем часовой пояс
        shift_start = shift_start.replace(tzinfo=tz)
        current_time = current_time.replace(tzinfo=tz)

        return current_time >= shift_start

    except Exception:
        return False


def validate_time_range(time_str: str) -> Tuple[bool, str]:
    """Валидирует строку временного диапазона.

    Args:
        time_str: Строка времени в формате HH:MM-HH:MM

    Returns:
        Кортеж (is_valid, error_message)
    """
    # Проверяем формат времени
    time_pattern = r"^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$"
    match = re.match(time_pattern, time_str.strip())

    if not match:
        return False, "Неверный формат времени. Используй формат: 09:00-13:00"

    start_hour, start_min, end_hour, end_min = map(int, match.groups())

    # Проверяем валидность времени
    if not (
        0 <= start_hour <= 23
        and 0 <= start_min <= 59
        and 0 <= end_hour <= 23
        and 0 <= end_min <= 59
    ):
        return False, "Неверное время. Часы: 0-23, минуты: 0-59"

    # Проверяем что минуты кратны 30
    if (start_min not in (0, 30)) or (end_min not in (0, 30)):
        return False, "Время должно начинаться и заканчиваться на 00 или 30 минутах"

    # Проверяем что время начала раньше времени окончания
    start_minutes = start_hour * 60 + start_min
    end_minutes = end_hour * 60 + end_min

    if start_minutes >= end_minutes:
        return False, "Время начала должно быть раньше времени окончания"

    # Проверяем минимальную продолжительность
    if end_minutes - start_minutes < 30:
        return False, "Подмена может составлять не менее 30 минут"

    return True, ""


def is_time_within_shift(time_str: str, shift_start: str, shift_end: str) -> bool:
    """Проверяет, находится ли время в пределах смены.

    Args:
        time_str: Временной диапазон в формате HH:MM-HH:MM
        shift_start: Время начала смены HH:MM
        shift_end: Время окончания смены HH:MM

    Returns:
        True если время в пределах смены, False если нет
    """
    try:
        # Разбираем время обмена
        start_time, end_time = time_str.split("-")
        start_time = start_time.strip()
        end_time = end_time.strip()

        # Переводим все в минуты для сравнения
        def time_to_minutes(time_str: str) -> int:
            h, m = map(int, time_str.split(":"))
            return h * 60 + m

        start_minutes = time_to_minutes(start_time)
        end_minutes = time_to_minutes(end_time)
        shift_start_minutes = time_to_minutes(shift_start)
        shift_end_minutes = time_to_minutes(shift_end)

        # Обработка ночных смен
        if shift_end_minutes < shift_start_minutes:
            shift_end_minutes += 24 * 60

        return start_minutes >= shift_start_minutes and end_minutes <= shift_end_minutes

    except Exception:
        return False


async def finish_exchange_create_dialog(
    _callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
) -> None:
    """Завершает процесс создания сделки и закрывает диалог.

    Args:
        _callback: Callback query от Telegram
        _button: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.done()


async def on_cancel_sell(
    _callback: CallbackQuery,
    _button: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик отмены создания предложения.

    Args:
        _callback: Callback query от Telegram
        _button: Кнопка отмены
        dialog_manager: Менеджер диалога
    """
    # Очищаем данные диалога
    dialog_manager.dialog_data.clear()
    # Возвращаемся к главному меню биржи
    await dialog_manager.switch_to(Exchanges.menu)


async def on_date_selected(
    callback: ChatEvent,
    _calendar: ManagedCalendar,
    dialog_manager: DialogManager,
    selected_date: datetime,
) -> None:
    """Обработчик выбора даты для предложения.

    Args:
        callback: Callback query от Telegram
        _calendar: Виджет календаря
        dialog_manager: Менеджер диалога
        selected_date: Выбранная дата
    """
    today = datetime.now().date()

    # Проверяем, что дата не в прошлом (можно продавать сегодня и в будущем)
    if selected_date < today:
        await callback.answer("❌ Нельзя выбрать прошедшую дату", show_alert=True)
        return

    shift_date_iso = selected_date.isoformat()

    # Проверяем, что пользователь работает в этот день
    shift_info = await get_user_shift_info(dialog_manager, shift_date_iso)
    if not shift_info:
        await callback.answer("❌ В выбранную дату у тебя нет смены", show_alert=True)
        return

    shift_start, shift_end, has_duty = shift_info

    # Проверяем существующие продажи на эту дату
    is_full_sold, sold_ranges, sold_strings = await get_existing_sales_for_date(
        dialog_manager, shift_date_iso, shift_start, shift_end
    )

    if is_full_sold:
        await callback.answer(
            "❌ Вся смена на эту дату уже продана или продается", show_alert=True
        )
        return

    # Сохраняем данные о выбранной дате и смене
    dialog_manager.dialog_data["shift_date"] = shift_date_iso
    dialog_manager.dialog_data["is_today"] = selected_date == today
    dialog_manager.dialog_data["shift_start"] = shift_start
    dialog_manager.dialog_data["shift_end"] = shift_end
    dialog_manager.dialog_data["has_duty"] = has_duty
    dialog_manager.dialog_data["sold_time_ranges"] = sold_ranges
    dialog_manager.dialog_data["sold_time_strings"] = sold_strings

    # Определяем следующий шаг в зависимости от статуса смены
    if selected_date == today and is_shift_started(shift_start, shift_date_iso):
        # Смена уже началась, сразу переходим к вводу времени
        dialog_manager.dialog_data["is_remaining_today"] = True
        await dialog_manager.switch_to(ExchangeCreateSell.hours)
    else:
        # Смена еще не началась, показываем варианты
        await dialog_manager.switch_to(ExchangeCreateSell.shift_type)


async def on_today_selected(
    callback: CallbackQuery, _button: Button, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Выбор текущей даты для сделки.

    Args:
        callback: Callback query от Telegram
        _button: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    today = datetime.now().date()
    shift_date_iso = today.isoformat()

    # Проверяем, что пользователь работает сегодня
    shift_info = await get_user_shift_info(dialog_manager, shift_date_iso)
    if not shift_info:
        await callback.answer("❌ Сегодня у тебя нет смены", show_alert=True)
        return

    shift_start, shift_end, has_duty = shift_info

    # Проверяем существующие продажи на сегодня
    is_full_sold, sold_ranges, sold_strings = await get_existing_sales_for_date(
        dialog_manager, shift_date_iso, shift_start, shift_end
    )

    if is_full_sold:
        await callback.answer(
            "❌ Вся смена на сегодня уже продана или продается", show_alert=True
        )
        return

    # Сохраняем данные о выбранной дате и смене
    dialog_manager.dialog_data["shift_date"] = shift_date_iso
    dialog_manager.dialog_data["is_today"] = True
    dialog_manager.dialog_data["shift_start"] = shift_start
    dialog_manager.dialog_data["shift_end"] = shift_end
    dialog_manager.dialog_data["has_duty"] = has_duty
    dialog_manager.dialog_data["sold_time_ranges"] = sold_ranges
    dialog_manager.dialog_data["sold_time_strings"] = sold_strings

    # Определяем следующий шаг в зависимости от статуса смены
    if is_shift_started(shift_start, shift_date_iso):
        # Смена уже началась, сразу переходим к вводу времени
        dialog_manager.dialog_data["is_remaining_today"] = True
        await dialog_manager.switch_to(ExchangeCreateSell.hours)
    else:
        # Смена еще не началась, показываем варианты
        await dialog_manager.switch_to(ExchangeCreateSell.shift_type)


async def on_hours_selected(
    callback: CallbackQuery,
    _select: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Обработчик выбора типа смены (полная/частичная).

    Args:
        callback: Callback query от Telegram
        _select: Виджет селектора
        dialog_manager: Менеджер диалога
        item_id: Идентификатор выбранного предмета
    """
    shift_date_str = dialog_manager.dialog_data["shift_date"]
    shift_start = dialog_manager.dialog_data["shift_start"]
    shift_end = dialog_manager.dialog_data["shift_end"]

    if item_id == "full":
        # Полная смена - используем полное время смены
        try:
            shift_date = datetime.fromisoformat(shift_date_str)
            start_datetime = datetime.combine(
                shift_date.date(), datetime.strptime(shift_start, "%H:%M").time()
            )
            end_datetime = datetime.combine(
                shift_date.date(), datetime.strptime(shift_end, "%H:%M").time()
            )

            # Проверяем на пересечение с существующими обменами
            has_overlap = await check_existing_exchanges_overlap(
                dialog_manager, start_datetime, end_datetime
            )

            if has_overlap:
                await callback.answer(
                    "❌ У тебя уже есть активный обмен в это время", show_alert=True
                )
                return

            dialog_manager.dialog_data["start_time"] = start_datetime.isoformat()
            dialog_manager.dialog_data["end_time"] = end_datetime.isoformat()

            # Переходим к вводу цены
            await dialog_manager.switch_to(ExchangeCreateSell.price)

        except Exception as e:
            logger.error(f"[Биржа] Ошибка обработки полной смены: {e}")
            await callback.answer("❌ Произошла ошибка", show_alert=True)

    elif item_id == "partial":
        # Частичная смена - переходим к вводу времени
        await dialog_manager.switch_to(ExchangeCreateSell.hours)

    elif item_id == "remaining_today":
        # Оставшееся время сегодня
        dialog_manager.dialog_data["is_remaining_today"] = True
        await dialog_manager.switch_to(ExchangeCreateSell.hours)


async def on_time_input(
    message: Message,
    _text_input: ManagedTextInput,
    dialog_manager: DialogManager,
    data: str,
) -> None:
    """Обработчик ввода времени для предложения.

    Args:
        message: Сообщение клиента
        _text_input: Виджет ввода текста
        dialog_manager: Менеджер диалога
        data: Введенный текст
    """
    # Базовая валидация формата времени
    is_valid, error_message = validate_time_range(data)
    if not is_valid:
        await message.answer(f"<b>❌ {error_message}</b>")
        return

    shift_start = dialog_manager.dialog_data["shift_start"]
    shift_end = dialog_manager.dialog_data["shift_end"]

    # Проверяем, что время в пределах смены пользователя
    if not is_time_within_shift(data, shift_start, shift_end):
        await message.answer(
            f"❌ Время должно быть в пределах твоей смены: {shift_start}-{shift_end}"
        )
        return

    # Если это продажа оставшегося времени сегодня, проверим что время в будущем
    if dialog_manager.dialog_data.get("is_remaining_today"):
        start_time_str = data.split("-")[0].strip()
        current_time = datetime.now(tz=tz)
        current_minutes = current_time.hour * 60 + current_time.minute

        start_hour, start_min = map(int, start_time_str.split(":"))
        start_minutes = start_hour * 60 + start_min

        if start_minutes <= current_minutes:
            await message.answer(
                "❌ Время начала должно быть в будущем для продажи оставшегося времени"
            )
            return

    # Создаем datetime объекты для проверки пересечений
    shift_date_str = dialog_manager.dialog_data["shift_date"]
    shift_date = datetime.fromisoformat(shift_date_str)

    start_time_str, end_time_str = data.split("-")
    start_time_str = start_time_str.strip()
    end_time_str = end_time_str.strip()

    start_datetime = datetime.combine(
        shift_date.date(), datetime.strptime(start_time_str, "%H:%M").time()
    )
    end_datetime = datetime.combine(
        shift_date.date(), datetime.strptime(end_time_str, "%H:%M").time()
    )

    # Проверяем на пересечение с существующими обменами
    has_overlap = await check_existing_exchanges_overlap(
        dialog_manager, start_datetime, end_datetime
    )

    if has_overlap:
        await message.answer("❌ У тебя уже есть активный обмен в это время")
        return

    # Сохраняем время
    dialog_manager.dialog_data["start_time"] = start_datetime.isoformat()
    dialog_manager.dialog_data["end_time"] = end_datetime.isoformat()

    # Переходим к вводу цены
    await dialog_manager.switch_to(ExchangeCreateSell.price)


async def on_price_input(
    message: Message,
    _widget: ManagedTextInput,
    dialog_manager: DialogManager,
    data: str,
):
    """Обработчик ввода цены."""
    try:
        price = int(data)
        if price <= 0:
            await message.answer("❌ Цена должна быть больше 0")
            return
        if price > 50000:
            await message.answer("❌ Слишком большая цена (максимум 50,000 р.)")
            return

        # Сохраняем цену
        dialog_manager.dialog_data["price"] = price

        # Переходим к выбору времени оплаты
        await dialog_manager.switch_to(ExchangeCreateSell.payment_timing)

    except ValueError:
        await message.answer("❌ Введите корректную цену (например: 1000 или 1500)")


async def on_payment_timing_selected(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    item_id: str,
):
    """Обработчик выбора времени оплаты."""
    if item_id == "immediate":
        dialog_manager.dialog_data["payment_type"] = "immediate"
        dialog_manager.dialog_data["payment_date"] = None
        # Переходим к комментарию
        await dialog_manager.switch_to(ExchangeCreateSell.comment)
    elif item_id == "on_date":
        dialog_manager.dialog_data["payment_type"] = "on_date"
        # Переходим к выбору даты платежа
        await dialog_manager.switch_to(ExchangeCreateSell.payment_date)


async def on_payment_date_selected(
    callback: ChatEvent,
    _widget: ManagedCalendar,
    dialog_manager: DialogManager,
    selected_date: datetime,
):
    """Обработчик выбора даты платежа."""
    shift_date_str = dialog_manager.dialog_data.get("shift_date")
    if not shift_date_str:
        await callback.answer("❌ Ошибка: дата смены не найдена", show_alert=True)
        return

    # Проверяем, что дата платежа не в прошлом
    if selected_date < datetime.now().date():
        await callback.answer(
            "❌ Дата платежа не может быть в прошлом", show_alert=True
        )
        return

    # Сохраняем дату платежа
    dialog_manager.dialog_data["payment_date"] = selected_date.isoformat()

    # Переходим к комментарию
    await dialog_manager.switch_to(ExchangeCreateSell.comment)


async def on_confirm_sell(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
):
    """Обработчик подтверждения продажи."""
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user_id = dialog_manager.event.from_user.id

    try:
        # Получаем данные из диалога
        data = dialog_manager.dialog_data
        price = data["price"]
        start_time = datetime.fromisoformat(data["start_time"])
        end_time = (
            datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None
        )
        payment_type = data.get("payment_type", "immediate")
        payment_date = None

        if payment_type == "on_date" and data.get("payment_date"):
            payment_date = datetime.fromisoformat(data["payment_date"])

        # Проверяем бан пользователя
        if await stp_repo.exchange.is_user_exchange_banned(user_id):
            await callback.answer(
                "❌ Ты заблокирован от участия в бирже", show_alert=True
            )
            return

        # Получаем комментарий
        comment = data.get("comment")

        # Создаем обмен
        exchange = await stp_repo.exchange.create_exchange(
            seller_id=user_id,
            start_time=start_time,
            end_time=end_time,
            price=price,
            payment_type=payment_type,
            payment_date=payment_date,
            comment=comment,
            exchange_type="sell",  # Указываем тип обмена
            is_private=False,  # По умолчанию создаем публичные обмены
        )

        if exchange:
            await callback.answer("✅ Сделка добавлена на биржу!", show_alert=True)
            # Очищаем данные диалога
            dialog_manager.dialog_data.clear()
            await dialog_manager.start(
                Exchanges.my_detail, data={"exchange_id": exchange.id}
            )
        else:
            await callback.answer(
                "❌ Не удалось создать сделку. Попробуйте позже.", show_alert=True
            )

    except Exception as e:
        logger.error(f"[Биржа - Создание сделки] Произошла ошибка при публикации: {e}")
        await callback.answer(
            "❌ Произошла ошибка при создании сделки", show_alert=True
        )


async def on_comment_input(
    message: Message,
    _widget: ManagedTextInput,
    dialog_manager: DialogManager,
    data: str,
):
    """Обработчик ввода комментария."""
    # Проверяем длину комментария
    if len(data) > 500:
        await message.answer("❌ Комментарий слишком длинный (максимум 500 символов)")
        return

    # Сохраняем комментарий
    dialog_manager.dialog_data["comment"] = data.strip()

    # Переходим к подтверждению
    await dialog_manager.switch_to(ExchangeCreateSell.confirmation)


async def on_skip_comment(
    _callback: CallbackQuery,
    _button: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик пропуска комментария."""
    # Убираем комментарий из данных
    dialog_manager.dialog_data.pop("comment", None)

    # Переходим к подтверждению
    await dialog_manager.switch_to(ExchangeCreateSell.confirmation)

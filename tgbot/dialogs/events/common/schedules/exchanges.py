"""События для биржи подмен."""

import re
from datetime import datetime
from typing import Any, Optional, Tuple

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import ChatEvent, DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.kbd import Button, ManagedCalendar
from stp_database import MainRequestsRepo

from tgbot.dialogs.states.common.exchanges import Exchanges
from tgbot.services.files_processing.parsers.schedule import ScheduleParser


async def start_exchanges_dialog(
    _callback: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик перехода в диалог биржи подмен.

    Args:
        _callback: Callback query от Telegram
        _widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.start(
        Exchanges.menu,
    )


def parse_time_range(time_str: str) -> Tuple[int, int]:
    """Разбор строки временного диапазона на начальные и конечные минуты.

    Args:
        time_str: Строка с диапазоном времени, например «09:00-18:00»

    Returns:
        Кортеж (start_minutes, end_minutes)
    """
    try:
        if "-" not in time_str:
            return 0, 0

        start_time, end_time = time_str.split("-")
        start_parts = start_time.strip().split(":")
        end_parts = end_time.strip().split(":")

        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
        end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])

        # Работа в ночную смену
        if end_minutes < start_minutes:
            end_minutes += 24 * 60

        return start_minutes, end_minutes

    except (ValueError, IndexError):
        return 0, 0


async def get_user_real_shift(
    dialog_manager: DialogManager,
) -> Optional[Tuple[str, str]]:
    """Получает реальное время смены пользователя на выбранную дату.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Кортеж (start_time, end_time) или None если смена не найдена
    """
    shift_date = dialog_manager.dialog_data.get("shift_date")
    if not shift_date:
        return None

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

        schedule_with_duties = await parser.get_user_schedule_with_duties(
            employee.fullname,
            month_name,
            employee.division,
            stp_repo,
            current_day_only=False,
        )

        # Ищем смену на выбранную дату
        day_key = f"{date_obj.day:02d}"
        for day, (schedule, duty_info) in schedule_with_duties.items():
            if day_key in day and schedule:
                # Проверяем, есть ли время в графике
                time_pattern = r"(\d{1,2}:\d{2})-(\d{1,2}:\d{2})"
                match = re.search(time_pattern, schedule)
                if match:
                    return match.group(1), match.group(2)

        return None

    except Exception:
        return None


async def start_sell_process(
    _callback: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
):
    """Начать процесс продажи смены."""
    # Очищаем данные предыдущей сессии
    dialog_manager.dialog_data.clear()

    # Переходим к выбору даты
    await dialog_manager.switch_to(Exchanges.sell_date_select)


async def on_date_selected(
    callback: ChatEvent,
    _widget: ManagedCalendar,
    manager: DialogManager,
    selected_date: datetime.date,
):
    """Обработчик выбора даты смены."""
    today = datetime.now().date()

    # Проверяем, что дата не в прошлом (можно продавать сегодня и в будущем)
    if selected_date < today:
        await callback.answer("❌ Нельзя выбрать прошедшую дату", show_alert=True)
        return

    # Сохраняем выбранную дату
    manager.dialog_data["shift_date"] = selected_date.isoformat()
    manager.dialog_data["is_today"] = selected_date == today

    # Переходим к выбору часов
    await manager.switch_to(Exchanges.sell_hours_select)


async def on_hours_selected(
    _callback: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    item_id: str,
):
    """Обработчик выбора типа смены (полная/частичная)."""
    if item_id == "full":
        # Полная смена - используем реальное время смены
        dialog_manager.dialog_data["is_partial"] = False

        # Получаем реальное время смены пользователя
        real_shift = await get_user_real_shift(dialog_manager)
        if real_shift:
            shift_start_time, shift_end_time = real_shift
            dialog_manager.dialog_data["shift_start_time"] = shift_start_time
            dialog_manager.dialog_data["shift_end_time"] = shift_end_time
        else:
            # Fallback на значения по умолчанию
            dialog_manager.dialog_data["shift_start_time"] = "09:00"
            dialog_manager.dialog_data["shift_end_time"] = "18:00"

        # Переходим к вводу цены
        await dialog_manager.switch_to(Exchanges.sell_price_input)

    elif item_id == "partial":
        # Частичная смена - переходим к вводу времени
        dialog_manager.dialog_data["is_partial"] = True

        # Переходим к вводу времени
        await dialog_manager.switch_to(Exchanges.sell_time_input)

    elif item_id == "remaining_today":
        # Оставшееся время сегодня
        dialog_manager.dialog_data["is_partial"] = True
        dialog_manager.dialog_data["is_remaining_today"] = True

        # Переходим к вводу времени
        await dialog_manager.switch_to(Exchanges.sell_time_input)


async def on_time_input(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    data: str,
):
    """Обработчик ввода времени."""
    # Проверяем формат времени (09:00-13:00)
    time_pattern = r"^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$"
    match = re.match(time_pattern, data.strip())

    if not match:
        await message.answer(
            "❌ Неверный формат времени. Используйте формат: 09:00-13:00"
        )
        return

    start_hour, start_min, end_hour, end_min = map(int, match.groups())

    # Проверяем валидность времени
    if not (
        0 <= start_hour <= 23
        and 0 <= start_min <= 59
        and 0 <= end_hour <= 23
        and 0 <= end_min <= 59
    ):
        await message.answer("❌ Неверное время. Часы: 0-23, минуты: 0-59")
        return

    start_time = f"{start_hour:02d}:{start_min:02d}"
    end_time = f"{end_hour:02d}:{end_min:02d}"

    # Проверяем, что время начала меньше времени окончания
    start_minutes = start_hour * 60 + start_min
    end_minutes = end_hour * 60 + end_min

    if start_minutes >= end_minutes:
        await message.answer("❌ Время начала должно быть раньше времени окончания")
        return

    # Проверяем, что введенное время находится в пределах реальной смены пользователя
    real_shift = await get_user_real_shift(dialog_manager)
    if real_shift:
        real_start_time, real_end_time = real_shift
        real_start_minutes, real_end_minutes = parse_time_range(
            f"{real_start_time}-{real_end_time}"
        )

        # Проверяем, что время продажи находится в пределах реальной смены
        if start_minutes < real_start_minutes or end_minutes > real_end_minutes:
            await message.answer(
                f"❌ Время должно быть в пределах вашей смены: {real_start_time}-{real_end_time}"
            )
            return

    # Если это продажа оставшегося времени сегодня, проверим что время в будущем
    if dialog_manager.dialog_data.get("is_remaining_today"):
        current_time = datetime.now()
        current_minutes = current_time.hour * 60 + current_time.minute

        if start_minutes <= current_minutes:
            await message.answer(
                "❌ Время начала должно быть в будущем для продажи оставшегося времени"
            )
            return

    # Сохраняем время
    dialog_manager.dialog_data["shift_start_time"] = start_time
    dialog_manager.dialog_data["shift_end_time"] = end_time

    # Переходим к вводу цены
    await dialog_manager.switch_to(Exchanges.sell_price_input)


async def on_price_input(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    data: str,
):
    """Обработчик ввода цены."""
    try:
        price = float(data.replace(",", "."))
        if price <= 0:
            await message.answer("❌ Цена должна быть больше 0")
            return
        if price > 50000:
            await message.answer("❌ Слишком большая цена (максимум 50,000 руб.)")
            return

        # Сохраняем цену
        dialog_manager.dialog_data["price"] = price

        # Переходим к выбору времени оплаты
        await dialog_manager.switch_to(Exchanges.sell_payment_timing)

    except ValueError:
        await message.answer("❌ Введите корректную цену (например: 1000 или 1500.50)")


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
        # Переходим сразу к подтверждению
        await dialog_manager.switch_to(Exchanges.sell_confirmation)
    elif item_id == "on_date":
        dialog_manager.dialog_data["payment_type"] = "on_date"
        # Переходим к выбору даты платежа
        await dialog_manager.switch_to(Exchanges.sell_payment_date)


async def on_payment_date_selected(
    callback: ChatEvent,
    widget: ManagedCalendar,
    manager: DialogManager,
    selected_date: datetime.date,
):
    """Обработчик выбора даты платежа."""
    shift_date_str = manager.dialog_data.get("shift_date")
    if not shift_date_str:
        await callback.answer("❌ Ошибка: дата смены не найдена", show_alert=True)
        return

    shift_date = datetime.fromisoformat(shift_date_str).date()

    # Проверяем, что дата платежа не после даты смены
    if selected_date > shift_date:
        await callback.answer(
            "❌ Дата платежа не может быть позже даты смены", show_alert=True
        )
        return

    # Проверяем, что дата платежа не в прошлом
    if selected_date < datetime.now().date():
        await callback.answer(
            "❌ Дата платежа не может быть в прошлом", show_alert=True
        )
        return

    # Сохраняем дату платежа
    manager.dialog_data["payment_date"] = selected_date.isoformat()

    # Переходим к подтверждению
    await manager.switch_to(Exchanges.sell_confirmation)


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
        shift_date = datetime.fromisoformat(data["shift_date"])
        price = data["price"]
        is_partial = data.get("is_partial", False)
        shift_start_time = data.get("shift_start_time", "09:00")
        shift_end_time = data.get("shift_end_time")
        payment_type = data.get("payment_type", "immediate")
        payment_date = None

        if payment_type == "on_date" and data.get("payment_date"):
            payment_date = datetime.fromisoformat(data["payment_date"])

        # Проверяем бан пользователя
        if await stp_repo.exchange.is_user_exchange_banned(user_id):
            await callback.answer(
                "❌ Вы заблокированы от участия в бирже подмен", show_alert=True
            )
            return

        # Создаем обмен
        exchange = await stp_repo.exchange.create_exchange(
            seller_id=user_id,
            shift_date=shift_date,
            shift_start_time=shift_start_time,
            price=price,
            is_partial=is_partial,
            shift_end_time=shift_end_time,
            payment_type=payment_type,
            payment_date=payment_date,
        )

        if exchange:
            await callback.answer("✅ Ваша смена добавлена на биржу!", show_alert=True)
            # Очищаем данные диалога
            dialog_manager.dialog_data.clear()
            # Возвращаемся к главному меню биржи
            await dialog_manager.switch_to(Exchanges.menu)
        else:
            await callback.answer(
                "❌ Не удалось создать объявление. Попробуйте позже.", show_alert=True
            )

    except Exception:
        await callback.answer(
            "❌ Произошла ошибка при создании объявления", show_alert=True
        )


async def on_cancel_sell(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
):
    """Обработчик отмены продажи."""
    # Очищаем данные диалога
    dialog_manager.dialog_data.clear()
    # Возвращаемся к главному меню биржи
    await dialog_manager.switch_to(Exchanges.menu)


async def on_exchange_buy_selected(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    item_id: str,
):
    """Обработчик выбора обмена для покупки."""
    try:
        exchange_id = int(item_id)
        dialog_manager.dialog_data["exchange_id"] = exchange_id
        await dialog_manager.switch_to(Exchanges.buy_detail)
    except (ValueError, TypeError):
        await callback.answer("❌ Ошибка выбора обмена", show_alert=True)


async def on_exchange_sell_selected(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    item_id: str,
):
    """Обработчик выбора собственного обмена."""
    try:
        exchange_id = int(item_id)
        dialog_manager.dialog_data["exchange_id"] = exchange_id
        await dialog_manager.switch_to(Exchanges.sell_detail)
    except (ValueError, TypeError):
        await callback.answer("❌ Ошибка выбора обмена", show_alert=True)


async def on_exchange_apply(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
):
    """Обработчик покупки обмена."""
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user_id = dialog_manager.event.from_user.id
    exchange_id = dialog_manager.dialog_data.get("exchange_id")

    if not exchange_id:
        await callback.answer("❌ Обмен не найден", show_alert=True)
        return

    try:
        # Проверяем бан пользователя
        if await stp_repo.exchange.is_user_exchange_banned(user_id):
            await callback.answer(
                "❌ Вы заблокированы от участия в бирже подмен", show_alert=True
            )
            return

        # Получаем обмен
        exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
        if not exchange or exchange.status != "active":
            await callback.answer("❌ Обмен недоступен", show_alert=True)
            return

        # Проверяем, что это не собственный обмен
        if exchange.seller_id == user_id:
            await callback.answer("❌ Нельзя купить собственный обмен", show_alert=True)
            return

        # Применяем обмен (покупаем)
        success = await stp_repo.exchange.buy_exchange(exchange_id, user_id)

        if success:
            await callback.answer(
                "✅ Обмен успешно куплен! Свяжитесь с продавцом для деталей.",
                show_alert=True,
            )
            # Очищаем данные диалога
            dialog_manager.dialog_data.clear()
            # Возвращаемся к главному меню биржи
            await dialog_manager.switch_to(Exchanges.menu)
        else:
            await callback.answer(
                "❌ Не удалось купить обмен. Попробуйте позже.", show_alert=True
            )

    except Exception:
        await callback.answer("❌ Произошла ошибка при покупке обмена", show_alert=True)


async def on_exchange_buy_cancel(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
):
    """Обработчик отмены покупки обмена."""
    # Очищаем данные и возвращаемся к списку покупок
    dialog_manager.dialog_data.pop("exchange_id", None)
    await dialog_manager.switch_to(Exchanges.buy)


async def on_exchange_cancel(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
):
    """Обработчик отмены собственного обмена."""
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user_id = dialog_manager.event.from_user.id
    exchange_id = dialog_manager.dialog_data.get("exchange_id")

    if not exchange_id:
        await callback.answer("❌ Обмен не найден", show_alert=True)
        return

    try:
        # Получаем обмен
        exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
        if not exchange:
            await callback.answer("❌ Обмен не найден", show_alert=True)
            return

        # Проверяем, что это обмен пользователя
        if exchange.seller_id != user_id:
            await callback.answer(
                "❌ Можно отменять только свои обмены", show_alert=True
            )
            return

        # Проверяем статус обмена
        if exchange.status != "active":
            await callback.answer(
                "❌ Можно отменять только активные обмены", show_alert=True
            )
            return

        # Отменяем обмен
        success = await stp_repo.exchange.cancel_exchange(exchange_id)

        if success:
            await callback.answer("✅ Обмен успешно отменен", show_alert=True)
            # Очищаем данные диалога
            dialog_manager.dialog_data.clear()
            # Возвращаемся к меню продажи
            await dialog_manager.switch_to(Exchanges.sell)
        else:
            await callback.answer(
                "❌ Не удалось отменить обмен. Попробуйте позже.", show_alert=True
            )

    except Exception:
        await callback.answer("❌ Произошла ошибка при отмене обмена", show_alert=True)

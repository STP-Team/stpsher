import logging
import re
from datetime import datetime
from typing import Any, Optional, Tuple

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import ChatEvent, DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.kbd import Button, ManagedCalendar, Select
from stp_database import MainRequestsRepo

from tgbot.dialogs.states.common.exchanges import (
    ExchangeCreateSell,
    Exchanges,
)
from tgbot.services.files_processing.parsers.schedule import ScheduleParser

logger = logging.getLogger(__name__)


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


async def get_user_shift(
    dialog_manager: DialogManager,
) -> Optional[Tuple[str, str]]:
    """Получает время смены пользователя на выбранную дату.

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


async def finish_exchange_create_dialog(
    _callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
) -> None:
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

    # Сохраняем выбранную дату
    dialog_manager.dialog_data["shift_date"] = selected_date.isoformat()
    dialog_manager.dialog_data["is_today"] = selected_date == today

    # Переходим к выбору часов
    await dialog_manager.switch_to(ExchangeCreateSell.shift_type)


async def on_hours_selected(
    _callback: CallbackQuery,
    _select: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Обработчик выбора типа смены (полная/частичная).

    Args:
        _callback: Callback query от Telegram
        _select: Виджет селектора
        dialog_manager: Менеджер диалога
        item_id: Идентификатор выбранного предмета
    """
    if item_id == "full":
        # Полная смена - используем реальное время смены
        dialog_manager.dialog_data["is_partial"] = False

        # Получаем реальное время смены пользователя
        real_shift = await get_user_shift(dialog_manager)
        try:
            shift_start_time, shift_end_time = real_shift
            dialog_manager.dialog_data["shift_start_time"] = shift_start_time
            dialog_manager.dialog_data["shift_end_time"] = shift_end_time
        except Exception as e:
            logger.error(f"[Биржа] Ошибка получения смены сотрудника: {e}")

        # Переходим к вводу цены
        await dialog_manager.switch_to(ExchangeCreateSell.price)

    elif item_id == "partial":
        # Частичная смена - переходим к вводу времени
        dialog_manager.dialog_data["is_partial"] = True

        # Переходим к вводу времени
        await dialog_manager.switch_to(ExchangeCreateSell.hours)

    elif item_id == "remaining_today":
        # Оставшееся время сегодня
        dialog_manager.dialog_data["is_partial"] = True
        dialog_manager.dialog_data["is_remaining_today"] = True

        # Переходим к вводу времени
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
    # Проверяем формат времени (09:00-13:00)
    time_pattern = r"^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$"
    match = re.match(time_pattern, data.strip())

    if not match:
        await message.answer(
            "<b>❌ Неверный формат времени</b>\n\nИспользуй формат: 09:00-13:00"
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
        await message.answer("<b>❌ Неверное время</b>\n\nЧасы: 0-23, минуты: 0-59")
        return

    if (start_min not in (0, 30)) or (end_min not in (0, 30)):
        await message.answer(
            "<b>❌ Неверное время</b>\n\nВремя подмены должно начинаться и заканчиваться либо на 00 минутах, либо на 30 минутах часа"
        )
        return

    start_time = f"{start_hour:02d}:{start_min:02d}"
    end_time = f"{end_hour:02d}:{end_min:02d}"

    # Проверяем, что время начала меньше времени окончания
    start_minutes = start_hour * 60 + start_min
    end_minutes = end_hour * 60 + end_min

    if start_minutes >= end_minutes:
        await message.answer(
            "<b>❌ Неверное время</b>\n\nВремя начала должно быть раньше времени окончания"
        )
        return

    if end_minutes - start_minutes < 30:
        await message.answer(
            "<b>❌ Неверное время</b>\n\nПодмена может составлять не менее 30 минут"
        )
        return

    # Проверяем, что введенное время находится в пределах реальной смены пользователя
    real_shift = await get_user_shift(dialog_manager)
    if real_shift:
        real_start_time, real_end_time = real_shift
        real_start_minutes, real_end_minutes = parse_time_range(
            f"{real_start_time}-{real_end_time}"
        )

        # Проверяем, что время продажи находится в пределах реальной смены
        if start_minutes < real_start_minutes or end_minutes > real_end_minutes:
            await message.answer(
                f"❌ Время должно быть в пределах твоей смены: {real_start_time}-{real_end_time}"
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

        # Получаем комментарий
        description = data.get("comment")

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
            description=description,
        )

        if exchange:
            await callback.answer("✅ Сделка добавлена на биржу!", show_alert=True)
            # Очищаем данные диалога
            dialog_manager.dialog_data.clear()
            # Возвращаемся к главному меню биржи
            await dialog_manager.done()
        else:
            await callback.answer(
                "❌ Не удалось создать предложение. Попробуйте позже.", show_alert=True
            )

    except Exception:
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


# Buy flow event handlers

"""События для биржи подмен."""

import logging
import re
from datetime import datetime
from typing import Any, Optional, Tuple

from aiogram.types import BufferedInputFile, CallbackQuery
from aiogram_dialog import ChatEvent, DialogManager
from aiogram_dialog.widgets.kbd import Button, ManagedCheckbox, Select
from stp_database import Employee, MainRequestsRepo

from tgbot.dialogs.getters.common.exchanges.exchanges import get_exchange_status
from tgbot.dialogs.states.common.exchanges import (
    ExchangeCreateBuy,
    ExchangeCreateSell,
    Exchanges,
)
from tgbot.dialogs.states.common.schedule import Schedules
from tgbot.misc.helpers import tz

logger = logging.getLogger(__name__)


async def get_shift_info_from_calendar_data(
    dialog_manager: DialogManager,
    selected_date: datetime,
) -> Optional[Tuple[str, str, bool, Optional[str], Optional[str]]]:
    """Получает информацию о смене из календарных данных.

    Args:
        dialog_manager: Менеджер диалога
        selected_date: Выбранная дата

    Returns:
        Кортеж (start_time, end_time, has_duty, duty_time, duty_type) или None если смена не найдена
    """
    # Проверяем календарные данные
    shift_dates = dialog_manager.dialog_data.get("shift_dates", {})
    if not shift_dates:
        return None

    # Формируем ключи для поиска
    month_day_key = f"{selected_date.month:02d}_{selected_date.day:02d}"
    day_key = f"{selected_date.day:02d}"

    # Ищем данные о смене
    calendar_data = None
    if month_day_key in shift_dates:
        calendar_data = shift_dates[month_day_key]
    elif day_key in shift_dates:
        calendar_data = shift_dates[day_key]

    if not calendar_data or "schedule" not in calendar_data:
        return None

    # Извлекаем время из графика
    schedule_value = calendar_data["schedule"]
    time_pattern = r"(\d{1,2}:\d{2})-(\d{1,2}:\d{2})"
    match = re.search(time_pattern, schedule_value)

    if not match:
        return None

    shift_start = match.group(1)
    shift_end = match.group(2)

    # Получаем информацию о дежурствах из календарных данных
    duty_info = calendar_data.get("duty_info")
    has_duty = bool(duty_info)
    duty_time = duty_info if has_duty else None
    duty_type = None

    if duty_info and isinstance(duty_info, str):
        # Парсим информацию о дежурстве (формат: "время тип")
        duty_parts = duty_info.split()
        if len(duty_parts) >= 2 and duty_parts[-1] in ["С", "П"]:
            duty_type = duty_parts[-1]
            duty_time = " ".join(duty_parts[:-1])

    return shift_start, shift_end, has_duty, duty_time, duty_type


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


async def start_exchanges_dialog(
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик перехода в диалог биржи подмен.

    Args:
        _event: Callback query от Telegram
        _widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.start(
        Exchanges.menu,
    )


async def finish_exchanges_dialog(
    _event: CallbackQuery, _button: Button, dialog_manager: DialogManager
) -> None:
    """Завершение диалога биржи.

    Args:
        _event: Callback query от Telegrma
        _button: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.done()


async def open_my_schedule(
    _event: CallbackQuery, _widget: Button, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Открываем график пользователя.

    Args:
        _event: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.start(Schedules.my)


async def on_exchange_buy_selected(
    event: CallbackQuery,
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
        await event.answer("❌ Ошибка выбора обмена", show_alert=True)


async def on_exchange_sell_selected(
    event: CallbackQuery,
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
        await event.answer("❌ Ошибка выбора обмена", show_alert=True)


async def on_exchange_buy(
    event: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
):
    """Обработчик покупки предложения."""
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user_id = dialog_manager.event.from_user.id
    exchange_id = dialog_manager.dialog_data.get("exchange_id")

    if not exchange_id:
        await event.answer("❌ Обмен не найден", show_alert=True)
        return

    try:
        # Проверяем бан пользователя
        if await stp_repo.exchange.is_user_exchange_banned(user_id):
            await event.answer("❌ Ты заблокирован от участия в бирже", show_alert=True)
            return

        # Получаем обмен
        exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
        if not exchange or exchange.status != "active":
            await event.answer("❌ Сделка недоступна", show_alert=True)
            return

        # Покупаем обмен
        success = await stp_repo.exchange.buy_exchange(exchange_id, user_id)

        if success:
            await event.answer(
                "✅ Смена успешно куплена! Свяжись с продавцом для уточнения деталей",
                show_alert=True,
            )
            dialog_manager.dialog_data.clear()
            await dialog_manager.switch_to(Exchanges.buy)
        else:
            await event.answer(
                "❌ Не удалось купить смену. Попробуй позже.", show_alert=True
            )

    except Exception as e:
        logger.error(e)
        await event.answer("❌ Произошла ошибка при обработке запроса", show_alert=True)


async def on_exchange_sell(
    event: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
):
    """Обработчик покупки обмена или принятия запроса на покупку."""
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user_id = dialog_manager.event.from_user.id
    exchange_id = dialog_manager.dialog_data.get("exchange_id")

    if not exchange_id:
        await event.answer("❌ Обмен не найден", show_alert=True)
        return

    try:
        # Проверяем бан пользователя
        if await stp_repo.exchange.is_user_exchange_banned(user_id):
            await event.answer("❌ Ты заблокирован от участия в бирже", show_alert=True)
            return

        # Получаем обмен
        exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
        if not exchange or exchange.status != "active":
            await event.answer("❌ Сделка недоступна", show_alert=True)
            return

        # Покупаем обмен
        success = await stp_repo.exchange.buy_exchange(exchange_id, user_id)

        if success:
            await event.answer(
                "✅ Смена успешно куплена! Свяжись с продавцом для уточнения деталей",
                show_alert=True,
            )
            dialog_manager.dialog_data.clear()
            await dialog_manager.switch_to(Exchanges.buy)
        else:
            await event.answer(
                "❌ Не удалось купить смену. Попробуй позже.", show_alert=True
            )

    except Exception as e:
        logger.error(e)
        await event.answer("❌ Произошла ошибка при обработке запроса", show_alert=True)


async def on_exchange_buy_cancel(
    event: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
):
    """Обработчик отмены покупки обмена."""
    # Очищаем данные и возвращаемся к списку покупок
    dialog_manager.dialog_data.pop("exchange_id", None)
    await dialog_manager.switch_to(Exchanges.buy)


async def on_exchange_cancel(
    event: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
):
    """Обработчик отмены собственного обмена."""
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user_id = dialog_manager.event.from_user.id
    exchange_id = dialog_manager.dialog_data.get("exchange_id")

    if not exchange_id:
        await event.answer("❌ Обмен не найден", show_alert=True)
        return

    try:
        # Получаем обмен
        exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
        if not exchange:
            await event.answer("❌ Обмен не найден", show_alert=True)
            return

        # Проверяем, что это обмен пользователя
        if exchange.seller_id != user_id:
            await event.answer("❌ Можно отменять только свои обмены", show_alert=True)
            return

        # Проверяем статус обмена
        if exchange.status != "active":
            await event.answer(
                "❌ Можно отменять только активные обмены", show_alert=True
            )
            return

        # Отменяем обмен
        success = await stp_repo.exchange.cancel_exchange(exchange_id, user_id)

        if success:
            await event.answer("✅ Обмен успешно отменен", show_alert=True)
            # Очищаем данные диалога
            dialog_manager.dialog_data.clear()
            # Возвращаемся к меню продажи
            await dialog_manager.switch_to(Exchanges.sell)
        else:
            await event.answer(
                "❌ Не удалось отменить обмен. Попробуйте позже.", show_alert=True
            )

    except Exception:
        await event.answer("❌ Произошла ошибка при отмене обмена", show_alert=True)


async def on_my_exchange_selected(
    event: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    item_id: str,
):
    """Обработчик выбора собственного обмена из списка 'Мои сделки'."""
    try:
        exchange_id = int(item_id)
        dialog_manager.dialog_data["exchange_id"] = exchange_id
        await dialog_manager.switch_to(Exchanges.my_detail)
    except (ValueError, TypeError):
        await event.answer("❌ Ошибка выбора обмена", show_alert=True)


async def on_exchange_type_selected(
    _event: ChatEvent, _select: Select, dialog_manager: DialogManager, item_id: str
) -> None:
    """Обработчик выбора типа предложения.

    Args:
        _event: Callback query от Telegram
        _select: Виджет селектора
        dialog_manager: Менеджер диалога
        item_id: Идентификатор выбранного типа
    """
    dialog_manager.dialog_data["exchange_type"] = item_id

    # Маршрутизация в зависимости от типа операции
    if item_id == "buy":
        await dialog_manager.start(ExchangeCreateBuy.date)
    else:  # sell
        await dialog_manager.start(ExchangeCreateSell.date)


async def on_private_click(
    _event: CallbackQuery,
    widget: ManagedCheckbox,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Изменение приватности сделки.

    Args:
        _event: Callback query от Telegram
        widget: Виджет чекбокса
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]

    exchange_id = (
        dialog_manager.dialog_data.get("exchange_id", None)
        or dialog_manager.start_data["exchange_id"]
    )

    await stp_repo.exchange.update_exchange(
        exchange_id, is_private=not widget.is_checked()
    )


async def on_paid_click(
    _event: CallbackQuery,
    widget: ManagedCheckbox,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Изменение статуса оплаты сделки.

    Args:
        _event: Callback query от Telegram
        widget: Виджет чекбокса
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]

    exchange_id = (
        dialog_manager.dialog_data.get("exchange_id", None)
        or dialog_manager.start_data["exchange_id"]
    )

    await stp_repo.exchange.update_exchange(
        exchange_id, is_paid=not widget.is_checked()
    )


async def on_in_schedule_click(
    _event: CallbackQuery,
    widget: ManagedCheckbox,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Изменение отображения сделки в графике.

    Args:
        _event: Callback query от Telegram
        widget: Виджет чекбокса
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user: Employee = dialog_manager.middleware_data["user"]

    exchange_id = (
        dialog_manager.dialog_data.get("exchange_id", None)
        or dialog_manager.start_data["exchange_id"]
    )

    exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)

    is_seller = exchange.seller_id == user.user_id

    if is_seller:
        await stp_repo.exchange.update_exchange(
            exchange_id, in_seller_schedule=not widget.is_checked()
        )
    else:
        await stp_repo.exchange.update_exchange(
            exchange_id, in_buyer_schedule=not widget.is_checked()
        )


async def on_activation_click(
    _event: CallbackQuery,
    widget: ManagedCheckbox,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Изменение статуса сделки.

    Args:
        _event: Callback query от Telegram
        widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]

    exchange_id = (
        dialog_manager.dialog_data.get("exchange_id", None)
        or dialog_manager.start_data["exchange_id"]
    )

    await stp_repo.exchange.update_exchange(
        exchange_id, status="canceled" if not widget.is_checked() else "active"
    )


async def on_delete_exchange(
    event: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    **_kwargs,
):
    """Удаление сделки.

    Args:
        event: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]

    exchange_id = (
        dialog_manager.dialog_data.get("exchange_id", None)
        or dialog_manager.start_data["exchange_id"]
    )

    await stp_repo.exchange.delete_exchange(exchange_id)
    await event.answer("🔥 Сделка удалена")
    await dialog_manager.switch_to(Exchanges.my)


async def on_set_paid(
    _event: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Отметка сделки оплаченной.

    Args:
        _event: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]

    exchange_id = (
        dialog_manager.dialog_data.get("exchange_id", None)
        or dialog_manager.start_data["exchange_id"]
    )

    await stp_repo.exchange.mark_exchange_paid(exchange_id)



async def on_edit_offer_price(
    _event: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик редактирования цены сделки.

    Args:
        _event: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.switch_to(Exchanges.edit_offer_price)


async def on_edit_offer_payment_timing(
    _event: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик редактирования условий оплаты сделки.

    Args:
        _event: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.switch_to(Exchanges.edit_offer_payment_timing)


async def on_edit_offer_comment(
    _event: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик редактирования комментария сделки.

    Args:
        _event: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.switch_to(Exchanges.edit_offer_comment)






async def on_edit_price_input(
    message: Any,
    widget: Any,
    dialog_manager: DialogManager,
    text: str,
    **_kwargs,
) -> None:
    """Обработчик ввода новой цены для сделки.

    Args:
        message: Сообщение от пользователя
        widget: Виджет ввода текста
        dialog_manager: Менеджер диалога
        text: Введенный текст
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]

    exchange_id = (
        dialog_manager.dialog_data.get("exchange_id", None)
        or dialog_manager.start_data["exchange_id"]
    )

    if not exchange_id:
        await message.answer("❌ Ошибка: сделка не найдена")
        return

    try:
        price = int(text.strip())
        if price < 1 or price > 50000:
            await message.answer("❌ Цена должна быть от 1 до 50,000 рублей")
            return

        await stp_repo.exchange.update_exchange_price(exchange_id, price)
        await message.answer("✅ Цена успешно обновлена")
        await dialog_manager.switch_to(Exchanges.my_detail)
    except ValueError:
        await message.answer("❌ Цена должна быть числом")
    except Exception as e:
        logger.error(f"Error updating exchange price: {e}")
        await message.answer("❌ Ошибка при обновлении цены")


async def on_edit_payment_timing_selected(
    _event: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    item_id: str,
    **_kwargs,
) -> None:
    """Обработчик выбора условий оплаты.

    Args:
        _event: Callback query от Telegram
        _widget: Виджет селектора
        dialog_manager: Менеджер диалога
        item_id: Выбранный тип оплаты
    """
    dialog_manager.dialog_data["edit_payment_type"] = item_id

    if item_id == "on_date":
        await dialog_manager.switch_to(Exchanges.edit_offer_payment_date)
    else:  # immediate
        # Сразу обновляем в базе
        await _update_payment_timing(dialog_manager, item_id, None)


async def on_edit_payment_date_selected(
    _event: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    selected_date: datetime,
) -> None:
    """Обработчик выбора даты оплаты.

    Args:
        _event: Callback query от Telegram
        _widget: Виджет календаря
        dialog_manager: Менеджер диалога
        selected_date: Выбранная дата
    """
    payment_type = dialog_manager.dialog_data.get("edit_payment_type", "on_date")

    await _update_payment_timing(dialog_manager, payment_type, selected_date)


async def _update_payment_timing(
    dialog_manager: DialogManager, payment_type: str, payment_date: datetime = None
):
    """Вспомогательная функция для обновления условий оплаты."""
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]

    exchange_id = (
        dialog_manager.dialog_data.get("exchange_id", None)
        or dialog_manager.start_data["exchange_id"]
    )

    if not exchange_id:
        return

    try:
        await stp_repo.exchange.update_payment_timing(
            exchange_id, payment_type, payment_date
        )
        await dialog_manager.switch_to(Exchanges.my_detail)
    except Exception as e:
        logger.error(f"Error updating payment timing: {e}")


async def on_edit_comment_input(
    message: Any,
    widget: Any,
    dialog_manager: DialogManager,
    text: str,
    **_kwargs,
) -> None:
    """Обработчик ввода нового комментария для сделки.

    Args:
        message: Сообщение от пользователя
        widget: Виджет ввода текста
        dialog_manager: Менеджер диалога
        text: Введенный текст
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]

    exchange_id = (
        dialog_manager.dialog_data.get("exchange_id", None)
        or dialog_manager.start_data["exchange_id"]
    )

    if not exchange_id:
        await message.answer("❌ Ошибка: сделка не найдена")
        return

    comment = text.strip()
    if len(comment) > 500:
        await message.answer("❌ Комментарий не может быть длиннее 500 символов")
        return

    try:
        await stp_repo.exchange.update_exchange_comment(exchange_id, comment)
        await message.answer("✅ Комментарий успешно обновлен")
        await dialog_manager.switch_to(Exchanges.my_detail)
    except Exception as e:
        logger.error(f"Error updating exchange comment: {e}")
        await message.answer("❌ Ошибка при обновлении комментария")


async def on_add_to_calendar(
    event: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user: Employee = dialog_manager.middleware_data["user"]

    exchange_id = (
        dialog_manager.dialog_data.get("exchange_id", None)
        or dialog_manager.start_data["exchange_id"]
    )

    exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
    if not exchange:
        return

    if exchange.seller_id == user.user_id:
        second_party = exchange.buyer_id
    else:
        second_party = exchange.seller_id

    second_party = await stp_repo.employee.get_users(user_id=second_party)

    dt_format = "%Y%m%dT%H%M%S"
    dtstamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")

    # Защита от None значений в датах
    if exchange.start_time:
        dtstart = exchange.start_time.strftime(dt_format)
    else:
        dtstart = datetime.now().strftime(dt_format)

    if exchange.end_time:
        dtend = exchange.end_time.strftime(dt_format)
    else:
        dtend = datetime.now().strftime(dt_format)

    ics_text = f"""BEGIN:VCALENDAR
VERSION:2.0
CALSCALE:GREGORIAN
PRODID:-//STPsher//EN
BEGIN:VEVENT
UID:{exchange.id}@stpsher
DTSTAMP:{dtstamp}
DTSTART:{dtstart}
DTEND:{dtend}
SUMMARY:Подмена
DESCRIPTION:Подмена {second_party.fullname}
LOCATION:Дом.ру
END:VEVENT
END:VCALENDAR
"""

    buffered_file = BufferedInputFile(ics_text.encode("utf-8"), filename="Подмена.ics")

    await event.bot.send_document(
        chat_id=event.from_user.id,
        document=buffered_file,
        caption="""<b>✍🏼 Подмена в календарь</b>

Нажми на файл для добавления подмены в календарь""",
    )


async def on_reset_filters(
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик сброса фильтров и сортировки к значениям по умолчанию.

    Args:
        _event: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    from aiogram_dialog.widgets.kbd import ManagedRadio, ManagedToggle

    try:
        # Сбрасываем фильтры к значениям по умолчанию
        day_filter_checkbox: ManagedRadio = dialog_manager.find("day_filter")
        if day_filter_checkbox:
            await day_filter_checkbox.set_checked("all")

        shift_filter_checkbox: ManagedRadio = dialog_manager.find("shift_filter")
        if shift_filter_checkbox:
            await shift_filter_checkbox.set_checked("no_shift")

        date_sort_toggle: ManagedToggle = dialog_manager.find("date_sort")
        if date_sort_toggle:
            await date_sort_toggle.set_checked("nearest")

        price_sort_toggle: ManagedToggle = dialog_manager.find("price_sort")
        if price_sort_toggle:
            await price_sort_toggle.set_checked("cheap")

    except Exception as e:
        logger.error(f"[Биржа] Ошибка при сбросе фильтров: {e}")

"""События для биржи подмен."""

import logging
import re
from datetime import datetime
from typing import Optional, Tuple

from aiogram import Bot
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.deep_linking import create_start_link
from aiogram_dialog import ChatEvent, DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.kbd import Button, Calendar, ManagedCheckbox, Select
from stp_database import Employee, MainRequestsRepo

from tgbot.dialogs.getters.common.exchanges.exchanges import _get_exchange_status
from tgbot.dialogs.states.common.exchanges import (
    ExchangeCreateBuy,
    ExchangeCreateSell,
    Exchanges,
)
from tgbot.dialogs.states.common.schedule import Schedules
from tgbot.misc.helpers import format_fullname, tz_perm
from tgbot.services.notifications.subscription_matcher import (
    notify_matching_subscriptions,
)

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
            user_id=user_id, owner_intent="sold"
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
            status_text = await _get_exchange_status(exchange)
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
        current_time = datetime.now(tz=tz_perm)
        shift_date_obj = datetime.fromisoformat(shift_date).date()

        # Если дата не сегодня, то смена не может быть начата
        if shift_date_obj != current_time.date():
            return False

        # Создаем datetime для времени начала смены
        shift_start = datetime.combine(
            shift_date_obj, datetime.strptime(shift_start_time, "%H:%M").time()
        )

        # Добавляем часовой пояс
        shift_start = shift_start.replace(tzinfo=tz_perm)
        current_time = current_time.replace(tzinfo=tz_perm)

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
    _event: CallbackQuery, _widget: Button, dialog_manager: DialogManager
) -> None:
    """Завершение диалога биржи.

    Args:
        _event: Callback query от Telegrma
        _widget: Виджет кнопки
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
    _widget: Select,
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
    _widget: Select,
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
    _widget: Button,
    dialog_manager: DialogManager,
):
    """Обработчик покупки sell offer."""
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user_id = dialog_manager.event.from_user.id

    exchange_id = dialog_manager.dialog_data["exchange_id"]

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

        # Проверяем что это sell offer
        if exchange.owner_intent != "sell":
            await event.answer("❌ Это не предложение продажи", show_alert=True)
            return

        # Пользователь покупает существующее предложение продажи
        dialog_manager.dialog_data["original_exchange"] = {
            "id": exchange.id,
            "start_time": exchange.start_time.isoformat() if exchange.start_time else None,
            "end_time": exchange.end_time.isoformat() if exchange.end_time else None,
            "price": exchange.price,
            "owner_id": exchange.owner_id,  # Создатель обмена
        }
        # Переходим к экрану выбора времени для покупки
        await dialog_manager.switch_to(Exchanges.buy_time_selection)

    except Exception as e:
        logger.error(e)
        await event.answer("❌ Произошла ошибка при обработке запроса", show_alert=True)


async def on_exchange_sell(
    event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
):
    """Обработчик ответа на buy request (продажа)."""
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    exchange_id = dialog_manager.dialog_data["exchange_id"]
    user_id = dialog_manager.event.from_user.id

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

        # Проверяем что это buy request
        if exchange.owner_intent != "buy":
            await event.answer("❌ Это не запрос покупки", show_alert=True)
            return

        # Пользователь отвечает на запрос покупки
        dialog_manager.dialog_data["buy_request"] = {
            "id": exchange.id,
            "start_time": exchange.start_time.isoformat() if exchange.start_time else None,
            "end_time": exchange.end_time.isoformat() if exchange.end_time else None,
            "price": exchange.price,
            "owner_id": exchange.owner_id,  # Создатель запроса покупки
        }
        # Переходим к экрану выбора времени для продажи
        await dialog_manager.switch_to(Exchanges.sell_time_selection)

    except Exception as e:
        logger.error(e)
        await event.answer("❌ Произошла ошибка при обработке запроса", show_alert=True)


async def on_my_exchange_selected(
    event: CallbackQuery,
    _widget: Select,
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
    exchange_id = dialog_manager.dialog_data["exchange_id"]

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
    exchange_id = dialog_manager.dialog_data["exchange_id"]

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
    exchange_id = dialog_manager.dialog_data["exchange_id"]

    exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)

    # Упрощаем логику: используем роли owner/counterpart
    is_owner = exchange.owner_id == user.user_id

    if is_owner:
        # Для владельца обмена управляем in_owner_schedule
        await stp_repo.exchange.update_exchange(
            exchange_id, in_owner_schedule=not widget.is_checked()
        )
    else:
        # Для counterpart управляем in_counterpart_schedule
        await stp_repo.exchange.update_exchange(
            exchange_id, in_counterpart_schedule=not widget.is_checked()
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
    exchange_id = dialog_manager.dialog_data["exchange_id"]

    new_status = "canceled" if not widget.is_checked() else "active"
    await stp_repo.exchange.update_exchange(exchange_id, status=new_status)

    # Проверяем подписки только при активации (переводе в статус "active")
    if new_status == "active":
        try:
            bot = dialog_manager.middleware_data["bot"]
            updated_exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
            if updated_exchange:
                # При реактивации считаем это новым обменом (без old_exchange)
                notifications_sent = await notify_matching_subscriptions(
                    bot, stp_repo, updated_exchange
                )
                if notifications_sent > 0:
                    logger.info(
                        f"Отправлено {notifications_sent} уведомлений о реактивированной сделке {exchange_id}"
                    )
        except Exception as e:
            logger.error(
                f"Ошибка отправки уведомлений о реактивированной сделке {exchange_id}: {e}"
            )


async def on_delete_exchange(
    event: CallbackQuery,
    _widget: Button,
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
    exchange_id = dialog_manager.dialog_data["exchange_id"]

    await stp_repo.exchange.delete_exchange(exchange_id)
    await event.answer("🔥 Сделка удалена")
    await dialog_manager.switch_to(Exchanges.my)


async def on_edit_offer_price(
    _event: CallbackQuery,
    _widget: Button,
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
    _widget: Button,
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
    _widget: Button,
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
    message: Message,
    _widget: ManagedTextInput,
    dialog_manager: DialogManager,
    text: str,
    **_kwargs,
) -> None:
    """Обработчик ввода новой цены для сделки.

    Args:
        message: Сообщение от пользователя
        _widget: Виджет ввода текста
        dialog_manager: Менеджер диалога
        text: Введенный текст
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    exchange_id = dialog_manager.dialog_data["exchange_id"]

    if not exchange_id:
        await message.answer("❌ Ошибка: сделка не найдена")
        return

    try:
        price = int(text.strip())
        if price < 1 or price > 50000:
            await message.answer("❌ Цена должна быть от 1 до 50,000 рублей")
            return

        # Получаем старую версию обмена перед обновлением
        old_exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)

        await stp_repo.exchange.update_exchange_price(exchange_id, price)

        # Проверяем подписки после обновления цены
        try:
            bot = dialog_manager.middleware_data["bot"]
            updated_exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
            if (
                updated_exchange
                and updated_exchange.status == "active"
                and old_exchange
            ):
                notifications_sent = await notify_matching_subscriptions(
                    bot, stp_repo, updated_exchange, old_exchange
                )
                if notifications_sent > 0:
                    logger.info(
                        f"Отправлено {notifications_sent} уведомлений о обновленной сделке {exchange_id}"
                    )
        except Exception as e:
            logger.error(
                f"Ошибка отправки уведомлений об обновленной сделке {exchange_id}: {e}"
            )

        await message.answer("✅ Цена успешно обновлена")
        await dialog_manager.switch_to(Exchanges.my_detail)
    except ValueError:
        await message.answer("❌ Цена должна быть числом")
    except Exception as e:
        logger.error(f"Error updating exchange price: {e}")
        await message.answer("❌ Ошибка при обновлении цены")


async def on_edit_payment_timing_selected(
    _event: CallbackQuery,
    _widget: Select,
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
    _widget: Calendar,
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
    exchange_id = dialog_manager.dialog_data["exchange_id"]

    if not exchange_id:
        return

    try:
        # Получаем старую версию обмена перед обновлением
        old_exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)

        await stp_repo.exchange.update_payment_timing(
            exchange_id, payment_type, payment_date
        )

        # Проверяем подписки после обновления условий оплаты
        try:
            bot = dialog_manager.middleware_data["bot"]
            updated_exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
            if (
                updated_exchange
                and updated_exchange.status == "active"
                and old_exchange
            ):
                notifications_sent = await notify_matching_subscriptions(
                    bot, stp_repo, updated_exchange, old_exchange
                )
                if notifications_sent > 0:
                    logger.info(
                        f"Отправлено {notifications_sent} уведомлений о обновленной сделке {exchange_id}"
                    )
        except Exception as e:
            logger.error(
                f"Ошибка отправки уведомлений об обновленной сделке {exchange_id}: {e}"
            )

        await dialog_manager.switch_to(Exchanges.my_detail)
    except Exception as e:
        logger.error(f"Error updating payment timing: {e}")


async def on_edit_comment_input(
    message: Message,
    _widget: ManagedTextInput,
    dialog_manager: DialogManager,
    text: str,
    **_kwargs,
) -> None:
    """Обработчик ввода нового комментария для сделки.

    Args:
        message: Сообщение от пользователя
        _widget: Виджет ввода текста
        dialog_manager: Менеджер диалога
        text: Введенный текст
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    exchange_id = dialog_manager.dialog_data["exchange_id"]

    if not exchange_id:
        await message.answer("❌ Ошибка: сделка не найдена")
        return

    comment = text.strip()
    if len(comment) > 500:
        await message.answer("❌ Комментарий не может быть длиннее 500 символов")
        return

    try:
        # Получаем старую версию обмена перед обновлением
        old_exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)

        await stp_repo.exchange.update_exchange_comment(exchange_id, comment)

        # Проверяем подписки после обновления комментария
        try:
            bot = dialog_manager.middleware_data["bot"]
            updated_exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
            if (
                updated_exchange
                and updated_exchange.status == "active"
                and old_exchange
            ):
                notifications_sent = await notify_matching_subscriptions(
                    bot, stp_repo, updated_exchange, old_exchange
                )
                if notifications_sent > 0:
                    logger.info(
                        f"Отправлено {notifications_sent} уведомлений о обновленной сделке {exchange_id}"
                    )
        except Exception as e:
            logger.error(
                f"Ошибка отправки уведомлений об обновленной сделке {exchange_id}: {e}"
            )

        await message.answer("✅ Комментарий успешно обновлен")
        await dialog_manager.switch_to(Exchanges.my_detail)
    except Exception as e:
        logger.error(f"Error updating exchange comment: {e}")
        await message.answer("❌ Ошибка при обновлении комментария")


async def on_cancel_exchange(
    event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Отправляет предложение об отмене сделки партнеру.

    Args:
        event: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    bot: Bot = dialog_manager.middleware_data["bot"]
    user: Employee = dialog_manager.middleware_data["user"]
    exchange_id = dialog_manager.dialog_data["exchange_id"]
    if not exchange_id:
        await event.answer("❌ Сделка не найдена", show_alert=True)
        return

    try:
        exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
        if not exchange:
            await event.answer("❌ Сделка не найдена", show_alert=True)
            return

        # Проверяем статус сделки
        if exchange.status != "sold":
            await event.answer(
                "❌ Отменить можно только завершенные сделки", show_alert=True
            )
            return

        # Проверяем, не началось ли уже время сделки
        if exchange.start_time and tz_perm.localize(
            exchange.start_time
        ) <= datetime.now(tz=tz_perm):
            await event.answer(
                "❌ Нельзя отменить сделку после наступления времени начала",
                show_alert=True,
            )
            return

        # Определяем контрагента
        counterpart_id = (
            exchange.counterpart_id
            if exchange.owner_id == user.user_id
            else exchange.owner_id
        )

        if not counterpart_id:
            await event.answer("❌ Партнер не найден", show_alert=True)
            return

        # Создаем deeplink для просмотра сделки
        exchange_deeplink = await create_start_link(
            bot=bot, payload=f"exchange_{exchange.id}", encode=True
        )

        # Создаем deeplink для отмены сделки
        cancel_deeplink = await create_start_link(
            bot=bot, payload=f"cancel_{exchange.id}", encode=True
        )

        # Отправляем предложение об отмене контрагенту
        user_fullname = format_fullname(user, True, True)
        await bot.send_message(
            chat_id=counterpart_id,
            text=f"""✋ <b>Отмена сделки</b>

{user_fullname} предлагает отменить сделку #{exchange.id}

⚠️ <i>Отмена возможна только до наступления времени начала сделки</i>""",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🎭 Открыть сделку",
                            url=exchange_deeplink,
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="✋ Отменить сделку",
                            url=cancel_deeplink,
                        )
                    ],
                ]
            ),
        )

        await event.answer(
            "✅ Предложение об отмене отправлено партнеру", show_alert=True
        )

    except Exception as e:
        logger.error(f"Ошибка отправки предложения об отмене сделки {exchange_id}: {e}")
        await event.answer(
            "❌ Произошла ошибка при отправке предложения", show_alert=True
        )


async def on_add_to_calendar(
    event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Создает событие для Google и Apple календарей.

    Args:
        event: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user: Employee = dialog_manager.middleware_data["user"]
    exchange_id = dialog_manager.dialog_data["exchange_id"]

    exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
    if not exchange:
        return

    if exchange.owner_id == user.user_id:
        second_party = exchange.counterpart_id
    else:
        second_party = exchange.owner_id

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
            await shift_filter_checkbox.set_checked("all")

        date_sort_toggle: ManagedToggle = dialog_manager.find("date_sort")
        if date_sort_toggle:
            await date_sort_toggle.set_checked("nearest")

        price_sort_toggle: ManagedToggle = dialog_manager.find("price_sort")
        if price_sort_toggle:
            await price_sort_toggle.set_checked("cheap")

    except Exception as e:
        logger.error(f"[Биржа] Ошибка при сбросе фильтров: {e}")


async def on_buy_full_exchange(
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
):
    """Обработчик покупки полного обмена."""
    # Устанавливаем флаг, что покупаем полностью
    dialog_manager.dialog_data["buy_full"] = True
    # Переходим к подтверждению
    await dialog_manager.switch_to(Exchanges.buy_confirmation)


async def on_time_input(
    message: Message,
    _widget: ManagedTextInput,
    dialog_manager: DialogManager,
    text: str,
):
    """Обработчик ввода времени для частичной покупки."""
    try:
        # Валидируем формат времени
        if not _validate_time_format(text):
            await message.answer(
                "❌ Неверный формат времени. Используй формат ЧЧ:ММ-ЧЧ:ММ (например: 14:00-18:00)"
            )
            return

        # Парсим время
        start_str, end_str = text.split("-")

        # Валидируем границы времени
        original_exchange = dialog_manager.dialog_data.get("original_exchange")
        if not original_exchange:
            await message.answer("❌ Ошибка: данные обмена не найдены")
            return

        if not _validate_time_limits(start_str, end_str, original_exchange):
            original_start_dt = datetime.fromisoformat(original_exchange["start_time"]) if original_exchange["start_time"] else datetime.now()
            original_end_dt = datetime.fromisoformat(original_exchange["end_time"]) if original_exchange["end_time"] else datetime.now()
            original_start = original_start_dt.strftime("%H:%M")
            original_end = original_end_dt.strftime("%H:%M")
            await message.answer(
                f"❌ Время должно быть в пределах {original_start}-{original_end}"
            )
            return

        # Сохраняем выбранное время
        dialog_manager.dialog_data["selected_start_time"] = start_str
        dialog_manager.dialog_data["selected_end_time"] = end_str
        dialog_manager.dialog_data["buy_full"] = False

        # Переходим к подтверждению
        await dialog_manager.switch_to(Exchanges.buy_confirmation)

    except Exception as e:
        logger.error(f"[Биржа] Ошибка обработки времени: {e}")
        await message.answer("❌ Произошла ошибка при обработке времени")


async def on_buy_confirm(
    event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
):
    """Обработчик подтверждения покупки."""
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    bot: Bot = dialog_manager.middleware_data["bot"]
    user_id = dialog_manager.event.from_user.id

    buyer_user = await stp_repo.employee.get_users(user_id=user_id)
    formatted_buyer = format_fullname(buyer_user, True, True)
    try:
        original_exchange = dialog_manager.dialog_data.get("original_exchange")
        buy_full = dialog_manager.dialog_data.get("buy_full", False)

        if not original_exchange:
            await event.answer("❌ Ошибка: данные обмена не найдены", show_alert=True)
            return

        if buy_full:
            # Покупаем полный обмен
            success = await stp_repo.exchange.buy_exchange(
                original_exchange["id"], user_id
            )
            if success:
                await event.answer(
                    "✅ Смена успешно куплена полностью!\n\nНе забудьте создать подмену в WFM!",
                    show_alert=True,
                )
                deeplink = await create_start_link(
                    bot=bot, payload=f"exchange_{original_exchange['id']}", encode=True
                )
                await event.bot.send_message(
                    chat_id=original_exchange["owner_id"],
                    text=f"""🎉 <b>Сделка полностью закрыта</b>

🏷️ Номер сделки: #{original_exchange["id"]}
🤝 Партнер: {formatted_buyer}

<i>Не забудьте создать подмену на <b>WFM</b></i>""",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="🎭 Открыть сделку",
                                    url=deeplink,
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    text="🗓️ Открыть WFM",
                                    url="https://okc2.ertelecom.ru/wfm/vueapp/personal",
                                )
                            ],
                        ]
                    ),
                )
            else:
                await event.answer("❌ Не удалось купить смену", show_alert=True)
                return
        else:
            # Частичная покупка - обновляем существующий обмен и создаем новый
            new_exchanges = await _handle_partial_exchange(
                dialog_manager, stp_repo, user_id, bot
            )
            await event.answer(
                "✅ Часть смены успешно куплена!\n\nНе забудьте создать подмену в WFM!",
                show_alert=True,
            )
            deeplink = await create_start_link(
                bot=bot, payload=f"exchange_{original_exchange['id']}", encode=True
            )

            # Create deeplinks for new exchanges
            new_exchanges_text = ""
            if new_exchanges:
                new_exchanges_links = []
                for exchange in new_exchanges:
                    exchange_deeplink = await create_start_link(
                        bot=bot, payload=f"exchange_{exchange.id}", encode=True
                    )
                    new_exchanges_links.append(
                        f"🏷️ Номер сделки: <a href='{exchange_deeplink}'>#{exchange.id} ({exchange.start_time.strftime('%H:%M')}-{exchange.end_time.strftime('%H:%M')})</a>"
                    )
                new_exchanges_text = (
                    "Созданы новые сделки на оставшееся время:\n"
                    + "\n".join(new_exchanges_links)
                )

            await event.bot.send_message(
                chat_id=original_exchange["owner_id"],
                text=f"""🎉 <b>Сделка частично закрыта</b>

🏷️ Номер сделки: #{original_exchange["id"]}
🤝 Партнер: {formatted_buyer}

{new_exchanges_text}

<i>Не забудьте создать подмену на <b>WFM</b></i>""",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🎭 Открыть сделку",
                                url=deeplink,
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="🗓️ Открыть WFM",
                                url="https://okc2.ertelecom.ru/wfm/vueapp/personal",
                            )
                        ],
                    ]
                ),
            )

        # Очищаем данные и возвращаемся
        dialog_manager.dialog_data.clear()
        await dialog_manager.switch_to(Exchanges.buy)

    except Exception as e:
        logger.error(f"[Биржа] Ошибка подтверждения покупки: {e}")
        await event.answer("❌ Произошла ошибка при покупке", show_alert=True)


def _validate_time_format(time_str: str) -> bool:
    """Валидация формата времени ЧЧ:ММ-ЧЧ:ММ."""
    import re

    pattern = r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]-([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
    return bool(re.match(pattern, time_str))


def _validate_time_limits(
    start_str: str, end_str: str, original_exchange: dict
) -> bool:
    """Валидация что выбранное время находится в пределах оригинального обмена."""
    from datetime import datetime

    try:
        # Парсим время
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()

        # Получаем границы оригинального обмена
        original_start_dt = datetime.fromisoformat(original_exchange["start_time"]) if original_exchange["start_time"] else datetime.now()
        original_end_dt = datetime.fromisoformat(original_exchange["end_time"]) if original_exchange["end_time"] else datetime.now()
        original_start = original_start_dt.time()
        original_end = original_end_dt.time()

        # Проверяем что выбранное время в границах
        # Учитываем пересечение полуночи для времени
        def time_in_range(time_to_check, range_start, range_end):
            if range_start <= range_end:
                # Обычный диапазон времени (не пересекает полночь)
                return range_start <= time_to_check <= range_end
            else:
                # Диапазон пересекает полночь (например, 21:00-00:00)
                return time_to_check >= range_start or time_to_check <= range_end

        def is_valid_time_range(start, end, original_start, original_end):
            # Проверяем, что начальное и конечное время находятся в допустимых границах
            start_valid = time_in_range(start, original_start, original_end)
            end_valid = time_in_range(end, original_start, original_end)

            # Проверяем логичность диапазона (start != end)
            range_valid = start != end

            return start_valid and end_valid and range_valid

        return is_valid_time_range(start_time, end_time, original_start, original_end)
    except Exception:
        return False


async def _handle_partial_exchange(
    dialog_manager: DialogManager, stp_repo: MainRequestsRepo, user_id: int, bot: Bot
):
    """Обработка частичной покупки обмена."""
    from datetime import datetime

    original_exchange = dialog_manager.dialog_data.get("original_exchange")
    start_str = dialog_manager.dialog_data.get("selected_start_time")
    end_str = dialog_manager.dialog_data.get("selected_end_time")

    # Создаем datetime объекты для выбранного времени
    original_start_dt = datetime.fromisoformat(original_exchange["start_time"]) if original_exchange["start_time"] else datetime.now()
    exchange_date = original_start_dt.date()
    selected_start = datetime.combine(
        exchange_date, datetime.strptime(start_str, "%H:%M").time()
    )
    selected_end = datetime.combine(
        exchange_date, datetime.strptime(end_str, "%H:%M").time()
    )

    # Цена за час остается той же для всех частей
    price_per_hour = original_exchange["price"]

    # Обновляем существующий обмен на выбранное время и помечаем как проданный
    await stp_repo.exchange.update_exchange(
        original_exchange["id"],
        start_time=selected_start,
        end_time=selected_end,
        price=price_per_hour,  # Цена за час остается неизменной
        status="sold",
        counterpart_id=user_id,
    )

    # Создаем новые обмены для оставшегося времени
    original_start = datetime.fromisoformat(original_exchange["start_time"]) if original_exchange["start_time"] else datetime.now()
    original_end = datetime.fromisoformat(original_exchange["end_time"]) if original_exchange["end_time"] else datetime.now()

    new_exchanges = []
    # Создаем обмен для времени до выбранного диапазона
    if original_start < selected_start:
        new_exchange = await stp_repo.exchange.create_exchange(
            owner_id=original_exchange["owner_id"],
            start_time=original_start,
            end_time=selected_start,
            price=price_per_hour,  # Та же цена за час
            owner_intent="sell",
        )
        new_exchanges.append(new_exchange)

    # Создаем обмен для времени после выбранного диапазона
    if selected_end < original_end:
        new_exchange = await stp_repo.exchange.create_exchange(
            owner_id=original_exchange["owner_id"],
            start_time=selected_end,
            end_time=original_end,
            price=price_per_hour,  # Та же цена за час
            owner_intent="sell",
        )
        new_exchanges.append(new_exchange)

    # Уведомляем подписчиков о новых сделках
    try:
        total_notifications = 0
        for new_exchange in new_exchanges:
            if new_exchange:
                notifications_sent = await notify_matching_subscriptions(
                    bot, stp_repo, new_exchange
                )
                total_notifications += notifications_sent
        if total_notifications > 0:
            logger.info(
                f"Отправлено {total_notifications} уведомлений о новых сделках после частичной покупки"
            )
    except Exception as e:
        logger.error(f"Ошибка отправки уведомлений о новых сделках: {e}")

    return new_exchanges


async def on_offer_full_time(
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
):
    """Обработчик предложения полного времени в ответ на buy request."""
    # Устанавливаем флаг, что предлагаем полное время
    dialog_manager.dialog_data["offer_full"] = True
    # Переходим к подтверждению
    await dialog_manager.switch_to(Exchanges.sell_confirmation)


async def on_seller_time_input(
    message: Message,
    _widget: ManagedTextInput,
    dialog_manager: DialogManager,
    text: str,
):
    """Обработчик ввода времени продавцом для ответа на buy request."""
    try:
        # Валидируем формат времени
        if not _validate_time_format(text):
            await message.answer(
                "❌ Неверный формат времени. Используй формат ЧЧ:ММ-ЧЧ:ММ (например: 14:00-18:00)"
            )
            return

        # Парсим время
        start_str, end_str = text.split("-")

        # Валидируем границы времени против buy request
        buy_request = dialog_manager.dialog_data.get("buy_request")
        if not buy_request:
            await message.answer("❌ Ошибка: данные запроса покупки не найдены")
            return

        if not _validate_seller_time_limits(start_str, end_str, buy_request):
            request_start_dt = datetime.fromisoformat(buy_request["start_time"]) if buy_request["start_time"] else datetime.now()
            request_end_dt = datetime.fromisoformat(buy_request["end_time"]) if buy_request["end_time"] else datetime.now()
            request_start = request_start_dt.strftime("%H:%M")
            request_end = request_end_dt.strftime("%H:%M")
            await message.answer(
                f"❌ Время должно быть в пределах запрашиваемого диапазона {request_start}-{request_end}"
            )
            return

        # Сохраняем предложенное время
        dialog_manager.dialog_data["offered_start_time"] = start_str
        dialog_manager.dialog_data["offered_end_time"] = end_str
        dialog_manager.dialog_data["offer_full"] = False

        # Переходим к подтверждению
        await dialog_manager.switch_to(Exchanges.sell_confirmation)

    except Exception as e:
        logger.error(f"[Биржа] Ошибка обработки времени продавца: {e}")
        await message.answer("❌ Произошла ошибка при обработке времени")


async def on_sell_confirm(
    event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
):
    """Обработчик подтверждения предложения продажи."""
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    bot: Bot = dialog_manager.middleware_data["bot"]
    user_id = dialog_manager.event.from_user.id

    seller_user = await stp_repo.employee.get_users(user_id=user_id)
    formatted_seller = format_fullname(seller_user, True, True)

    try:
        buy_request = dialog_manager.dialog_data.get("buy_request")
        offer_full = dialog_manager.dialog_data.get("offer_full", False)

        if not buy_request:
            await event.answer(
                "❌ Ошибка: данные запроса покупки не найдены", show_alert=True
            )
            return

        # Проверяем, покрывает ли предложение полное время buy request
        is_full_time_offer = offer_full or _is_full_time_offer(
            dialog_manager, buy_request
        )

        if is_full_time_offer:
            # Предлагаем всё запрашиваемое время - устанавливаем counterpart_id
            await stp_repo.exchange.update_exchange(
                buy_request["id"], status="sold", counterpart_id=user_id
            )
            await event.answer(
                "✅ Сделка полностью закрыта!\n\nНе забудьте создать подмену в WFM!",
                show_alert=True,
            )

            # Уведомление покупателю о том, что его запрос принят
            deeplink = await create_start_link(
                bot=bot, payload=f"exchange_{buy_request['id']}", encode=True
            )
            await event.bot.send_message(
                chat_id=buy_request["owner_id"],
                text=f"""🎉 <b>Запрос покупки принят</b>

🏷️ Номер сделки: #{buy_request["id"]}
🤝 Партнер: {formatted_seller}

<i>Не забудьте создать подмену на <b>WFM</b></i>""",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🎭 Открыть сделку",
                                url=deeplink,
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="🗓️ Открыть WFM",
                                url="https://okc2.ertelecom.ru/wfm/vueapp/personal",
                            )
                        ],
                    ]
                ),
            )
        else:
            # Частичное предложение времени - обновляем buy request и создаем новые для оставшегося времени
            new_exchanges = await _handle_partial_sell_offer_new(
                dialog_manager, stp_repo, user_id, bot
            )
            await event.answer(
                "✅ Часы проданы!\n\nНе забудьте создать подмену в WFM!",
                show_alert=True,
            )

            # Уведомление покупателю о частичном принятии запроса
            deeplink = await create_start_link(
                bot=bot, payload=f"exchange_{buy_request['id']}", encode=True
            )

            # Create deeplinks for new exchanges
            new_exchanges_text = ""
            if new_exchanges:
                new_exchanges_links = []
                for exchange in new_exchanges:
                    exchange_deeplink = await create_start_link(
                        bot=bot, payload=f"exchange_{exchange.id}", encode=True
                    )
                    new_exchanges_links.append(
                        f"🏷️ Номер сделки: <a href='{exchange_deeplink}'>#{exchange.id} ({exchange.start_time.strftime('%H:%M')}-{exchange.end_time.strftime('%H:%M')})</a>"
                    )
                new_exchanges_text = (
                    "Созданы новые запросы на оставшееся время:\n"
                    + "\n".join(new_exchanges_links)
                )

            await event.bot.send_message(
                chat_id=buy_request["owner_id"],
                text=f"""🎉 <b>Запрос покупки частично принят</b>

🏷️ Номер сделки: #{buy_request["id"]}
🤝 Партнер: {formatted_seller}

{new_exchanges_text}

<i>Не забудьте создать подмену на <b>WFM</b></i>""",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🎭 Открыть сделку",
                                url=deeplink,
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="🗓️ Открыть WFM",
                                url="https://okc2.ertelecom.ru/wfm/vueapp/personal",
                            )
                        ],
                    ]
                ),
            )

        # Очищаем данные и возвращаемся
        dialog_manager.dialog_data.clear()
        await dialog_manager.switch_to(Exchanges.sell)

    except Exception as e:
        logger.error(f"[Биржа] Ошибка подтверждения предложения продажи: {e}")
        await event.answer(
            "❌ Произошла ошибка при отправке предложения", show_alert=True
        )


def _validate_seller_time_limits(
    start_str: str, end_str: str, buy_request: dict
) -> bool:
    """Валидация что предложенное время находится в пределах buy request."""
    from datetime import datetime

    try:
        # Парсим предложенное время
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()

        # Получаем границы buy request
        request_start_dt = datetime.fromisoformat(buy_request["start_time"]) if buy_request["start_time"] else datetime.now()
        request_end_dt = datetime.fromisoformat(buy_request["end_time"]) if buy_request["end_time"] else datetime.now()
        request_start = request_start_dt.time()
        request_end = request_end_dt.time()

        # Проверяем что предложенное время в границах запроса
        # Учитываем пересечение полуночи для времени
        def time_in_range(time_to_check, range_start, range_end):
            if range_start <= range_end:
                # Обычный диапазон времени (не пересекает полночь)
                return range_start <= time_to_check <= range_end
            else:
                # Диапазон пересекает полночь (например, 21:00-00:00)
                return time_to_check >= range_start or time_to_check <= range_end

        def is_valid_time_range(start, end, req_start, req_end):
            # Проверяем, что начальное и конечное время находятся в допустимых границах
            start_valid = time_in_range(start, req_start, req_end)
            end_valid = time_in_range(end, req_start, req_end)

            # Проверяем логичность диапазона (start != end)
            range_valid = start != end

            return start_valid and end_valid and range_valid

        return is_valid_time_range(start_time, end_time, request_start, request_end)
    except Exception:
        return False


async def _handle_partial_sell_offer(
    dialog_manager: DialogManager, stp_repo: MainRequestsRepo, user_id: int
):
    """Обработка частичного предложения времени продавцом (старая логика)."""

    buy_request = dialog_manager.dialog_data.get("buy_request")
    start_str = dialog_manager.dialog_data.get("offered_start_time")
    end_str = dialog_manager.dialog_data.get("offered_end_time")

    # Создаем datetime объекты для предложенного времени
    request_start_dt = datetime.fromisoformat(buy_request["start_time"]) if buy_request["start_time"] else datetime.now()
    request_date = request_start_dt.date()
    offered_start = datetime.combine(
        request_date, datetime.strptime(start_str, "%H:%M").time()
    )
    offered_end = datetime.combine(
        request_date, datetime.strptime(end_str, "%H:%M").time()
    )

    # Цена за час берется из buy request
    price_per_hour = buy_request["price"]

    # Создаем новое предложение продажи
    new_exchange_id = await stp_repo.exchange.create_exchange(
        owner_id=user_id,
        start_time=offered_start,
        end_time=offered_end,
        price=price_per_hour,
        owner_intent="sell",
        comment=f"Частичный ответ на запрос покупки #{buy_request['id']}",
    )

    if new_exchange_id:
        # Помечаем оригинальный buy request как частично выполненный
        # В данном случае оставляем активным, так как это частичное предложение
        pass


def _is_full_time_offer(dialog_manager: DialogManager, buy_request: dict) -> bool:
    """Проверяет, покрывает ли предложение полное время buy request."""
    if dialog_manager.dialog_data.get("offer_full", False):
        return True

    # Проверяем для частичного предложения времени
    start_str = dialog_manager.dialog_data.get("offered_start_time")
    end_str = dialog_manager.dialog_data.get("offered_end_time")

    if not start_str or not end_str:
        return False

    try:
        from datetime import datetime
        # Парсим предложенное время
        offered_start = datetime.strptime(start_str, "%H:%M").time()
        offered_end = datetime.strptime(end_str, "%H:%M").time()

        # Получаем время buy request
        request_start_dt = datetime.fromisoformat(buy_request["start_time"]) if buy_request["start_time"] else datetime.now()
        request_end_dt = datetime.fromisoformat(buy_request["end_time"]) if buy_request["end_time"] else datetime.now()
        request_start = request_start_dt.time()
        request_end = request_end_dt.time()

        # Проверяем, совпадает ли полностью
        return offered_start == request_start and offered_end == request_end
    except Exception:
        return False


async def _handle_partial_sell_offer_new(
    dialog_manager: DialogManager, stp_repo: MainRequestsRepo, user_id: int, bot: Bot
):
    """Обработка частичного предложения времени продавцом (новая логика как в покупке)."""
    from datetime import datetime

    buy_request = dialog_manager.dialog_data.get("buy_request")
    start_str = dialog_manager.dialog_data.get("offered_start_time")
    end_str = dialog_manager.dialog_data.get("offered_end_time")

    # Создаем datetime объекты для предложенного времени
    request_start_dt = datetime.fromisoformat(buy_request["start_time"]) if buy_request["start_time"] else datetime.now()
    request_date = request_start_dt.date()
    offered_start = datetime.combine(
        request_date, datetime.strptime(start_str, "%H:%M").time()
    )
    offered_end = datetime.combine(
        request_date, datetime.strptime(end_str, "%H:%M").time()
    )

    # Цена за час остается той же для всех частей
    price_per_hour = buy_request["price"]

    # Обновляем существующий buy request на предложенное время и помечаем как проданный
    await stp_repo.exchange.update_exchange(
        buy_request["id"],
        start_time=offered_start,
        end_time=offered_end,
        price=price_per_hour,  # Цена за час остается неизменной
        status="sold",
        counterpart_id=user_id,
    )

    # Создаем новые buy requests для оставшегося времени
    original_start = datetime.fromisoformat(buy_request["start_time"]) if buy_request["start_time"] else datetime.now()
    original_end = datetime.fromisoformat(buy_request["end_time"]) if buy_request["end_time"] else datetime.now()
    original_buyer_id = buy_request["owner_id"]  # Исправлено: используем owner_id

    new_exchanges = []
    # Создаем buy request для времени до предложенного диапазона
    if original_start < offered_start:
        new_exchange = await stp_repo.exchange.create_exchange(
            owner_id=original_buyer_id,
            start_time=original_start,
            end_time=offered_start,
            price=price_per_hour,  # Та же цена за час
            owner_intent="buy",
        )
        new_exchanges.append(new_exchange)

    # Создаем buy request для времени после предложенного диапазона
    if offered_end < original_end:
        new_exchange = await stp_repo.exchange.create_exchange(
            owner_id=original_buyer_id,
            start_time=offered_end,
            end_time=original_end,
            price=price_per_hour,  # Та же цена за час
            owner_intent="buy",
        )
        new_exchanges.append(new_exchange)

    # Уведомляем подписчиков о новых запросах на покупку
    try:
        total_notifications = 0
        for new_exchange in new_exchanges:
            if new_exchange:
                notifications_sent = await notify_matching_subscriptions(
                    bot, stp_repo, new_exchange
                )
                total_notifications += notifications_sent
        if total_notifications > 0:
            logger.info(
                f"Отправлено {total_notifications} уведомлений о новых запросах на покупку после частичной продажи"
            )
    except Exception as e:
        logger.error(f"Ошибка отправки уведомлений о новых запросах на покупку: {e}")

    return new_exchanges

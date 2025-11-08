"""Обработчики для диалога создания покупки на бирже."""

import logging
import re
from datetime import datetime

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.kbd import Button, ManagedCalendar
from stp_database import MainRequestsRepo

from tgbot.dialogs.states.common.exchanges import ExchangeCreateBuy, Exchanges
from tgbot.services.notifications.subscription_matcher import (
    notify_matching_subscriptions,
)

logger = logging.getLogger(__name__)


async def on_buy_date_selected(
    event: CallbackQuery,
    _calendar: ManagedCalendar,
    dialog_manager: DialogManager,
    selected_date: datetime,
) -> None:
    """Обработчик выбора даты для покупки."""
    today = datetime.now().date()

    # Проверяем, что дата не в прошлом
    if selected_date < today:
        await event.answer("❌ Нельзя выбрать прошедшую дату", show_alert=True)
        return

    # Сохраняем выбранную дату
    dialog_manager.dialog_data["buy_date"] = selected_date.isoformat()

    # Переходим к выбору времени
    await dialog_manager.switch_to(ExchangeCreateBuy.hours)


async def on_buy_date_skip(
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик пропуска выбора даты."""
    # Убираем дату из данных (любая дата)
    dialog_manager.dialog_data.pop("buy_date", None)
    dialog_manager.dialog_data["any_date"] = True

    # Переходим к выбору времени
    await dialog_manager.switch_to(ExchangeCreateBuy.hours)


async def on_buy_hours_input(
    message: Message,
    _text_input: ManagedTextInput,
    dialog_manager: DialogManager,
    data: str,
) -> None:
    """Обработчик ввода времени для покупки."""
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
            "<b>❌ Неверное время</b>\n\nВремя должно начинаться и заканчиваться либо на 00 минутах, либо на 30 минутах часа"
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
            "<b>❌ Неверное время</b>\n\nМинимальная продолжительность: 30 минут"
        )
        return

    # Создаем timestamp для start_time и end_time
    buy_date = dialog_manager.dialog_data.get("buy_date")

    if buy_date:
        # Если дата выбрана, создаем полные timestamp
        shift_date = datetime.fromisoformat(buy_date)
        start_datetime = datetime.combine(
            shift_date.date(), datetime.strptime(start_time, "%H:%M").time()
        )
        end_datetime = datetime.combine(
            shift_date.date(), datetime.strptime(end_time, "%H:%M").time()
        )

        dialog_manager.dialog_data["start_time"] = start_datetime.isoformat()
        dialog_manager.dialog_data["end_time"] = end_datetime.isoformat()
    else:
        # Если дата не выбрана, сохраняем только время
        dialog_manager.dialog_data["start_time"] = start_time
        dialog_manager.dialog_data["end_time"] = end_time

    # Переходим к вводу цены
    await dialog_manager.switch_to(ExchangeCreateBuy.price)


async def on_buy_hours_skip(
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик пропуска выбора времени."""
    # Убираем время из данных (любое время)
    dialog_manager.dialog_data.pop("start_time", None)
    dialog_manager.dialog_data.pop("end_time", None)
    dialog_manager.dialog_data["any_hours"] = True

    # Переходим к вводу цены
    await dialog_manager.switch_to(ExchangeCreateBuy.price)


async def on_buy_price_input(
    message: Message,
    _widget: ManagedTextInput,
    dialog_manager: DialogManager,
    data: str,
):
    """Обработчик ввода цены за час для покупки."""
    try:
        price_per_hour = int(data)
        if price_per_hour <= 0:
            await message.answer("❌ Цена должна быть больше 0")
            return
        if price_per_hour > 5000:
            await message.answer("❌ Слишком большая цена за час (максимум 5,000 ₽)")
            return

        # Сохраняем цену за час
        dialog_manager.dialog_data["buy_price_per_hour"] = price_per_hour

        # Переходим к комментарию
        await dialog_manager.switch_to(ExchangeCreateBuy.comment)

    except ValueError:
        await message.answer("❌ Введите корректную цену (например: 500 или 750)")


async def on_buy_skip_comment(
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик пропуска комментария для покупки."""
    # Убираем комментарий из данных
    dialog_manager.dialog_data.pop("buy_comment", None)

    # Переходим к подтверждению
    await dialog_manager.switch_to(ExchangeCreateBuy.confirmation)


async def on_buy_comment_input(
    message: Message,
    _widget: ManagedTextInput,
    dialog_manager: DialogManager,
    data: str,
):
    """Обработчик ввода комментария для покупки."""
    # Проверяем длину комментария
    if len(data) > 500:
        await message.answer("❌ Комментарий слишком длинный (максимум 500 символов)")
        return

    # Сохраняем комментарий
    dialog_manager.dialog_data["buy_comment"] = data.strip()

    # Переходим к подтверждению
    await dialog_manager.switch_to(ExchangeCreateBuy.confirmation)


async def on_confirm_buy(
    event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
):
    """Обработчик подтверждения покупки."""
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user_id = dialog_manager.event.from_user.id

    try:
        # Получаем данные из диалога
        data = dialog_manager.dialog_data

        if data.get("start_time") and data.get("end_time"):
            # Если есть конкретное время
            if data.get("buy_date"):
                # Если есть конкретная дата
                start_time = datetime.fromisoformat(data["start_time"])
                end_time = datetime.fromisoformat(data["end_time"])
            else:
                # Если дата не указана, создаем timestamp с условной датой
                today = datetime.now().date()
                start_time_str = data["start_time"]
                end_time_str = data["end_time"]
                start_time = datetime.combine(
                    today, datetime.strptime(start_time_str, "%H:%M").time()
                )
                end_time = datetime.combine(
                    today, datetime.strptime(end_time_str, "%H:%M").time()
                )
        else:
            # Если время не указано, устанавливаем весь день (00:00 - 23:59)
            if data.get("buy_date"):
                # Если есть конкретная дата
                shift_date = datetime.fromisoformat(data["buy_date"])
                start_time = datetime.combine(
                    shift_date.date(), datetime.strptime("00:00", "%H:%M").time()
                )
                end_time = datetime.combine(
                    shift_date.date(), datetime.strptime("23:59", "%H:%M").time()
                )
            else:
                # Если дата не указана, используем сегодняшний день
                today = datetime.now().date()
                start_time = datetime.combine(
                    today, datetime.strptime("00:00", "%H:%M").time()
                )
                end_time = datetime.combine(
                    today, datetime.strptime("23:59", "%H:%M").time()
                )

        # Цена за час
        price_per_hour = data["buy_price_per_hour"]

        # Проверяем бан пользователя
        if await stp_repo.exchange.is_user_exchange_banned(user_id):
            await event.answer("❌ Ты заблокирован от участия в бирже", show_alert=True)
            return

        # Получаем комментарий
        comment = data.get("buy_comment")

        # Создаем запрос на покупку
        exchange = await stp_repo.exchange.create_exchange(
            owner_id=user_id,  # Пользователь создающий запрос на покупку
            start_time=start_time,
            end_time=end_time,
            price=price_per_hour,  # Цена за час
            payment_type="immediate",  # Для buy-запросов всегда немедленная оплата
            payment_date=None,
            comment=comment,
            owner_intent="buy",  # Указываем тип как покупка смены
            is_private=False,  # По умолчанию создаем публичные обмены
        )

        if exchange:
            # Уведомляем подписчиков о новом запросе на покупку
            bot = dialog_manager.middleware_data["bot"]
            try:
                notifications_sent = await notify_matching_subscriptions(
                    bot, stp_repo, exchange
                )
                if notifications_sent > 0:
                    logger.info(
                        f"Отправлено {notifications_sent} уведомлений о новом запросе на покупку {exchange.id}"
                    )
            except Exception as e:
                logger.error(
                    f"Ошибка отправки уведомлений о новом запросе на покупку {exchange.id}: {e}"
                )

            await event.answer(
                "✅ Запрос на покупку добавлен на биржу!", show_alert=True
            )
            # Очищаем данные диалога
            dialog_manager.dialog_data.clear()
            await dialog_manager.start(
                Exchanges.my_detail, data={"exchange_id": exchange.id}
            )
        else:
            await event.answer(
                "❌ Не удалось создать запрос. Попробуйте позже.", show_alert=True
            )

    except Exception:
        await event.answer("❌ Произошла ошибка при создании запроса", show_alert=True)

"""События для биржи подмен."""

import logging
from datetime import datetime
from typing import Any

from aiogram.types import BufferedInputFile, CallbackQuery
from aiogram_dialog import ChatEvent, DialogManager
from aiogram_dialog.widgets.kbd import Button, ManagedCalendar, ManagedCheckbox, Select
from stp_database import Employee, MainRequestsRepo

from tgbot.dialogs.states.common.exchanges import (
    ExchangeCreateBuy,
    ExchangeCreateSell,
    Exchanges,
)
from tgbot.dialogs.states.common.schedule import Schedules

logger = logging.getLogger(__name__)


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


async def on_edit_offer_date(
    _event: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик редактирования даты сделки.

    Args:
        _event: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.switch_to(Exchanges.edit_offer_date)


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


async def on_edit_date_selected(
    _event: CallbackQuery,
    _calendar: ManagedCalendar,
    dialog_manager: DialogManager,
    selected_date: datetime,
) -> None:
    """Обработчик выбора новой даты для сделки.

    Args:
        _event: Callback query от Telegram
        _widget: Виджет календаря
        dialog_manager: Менеджер диалога
    """
    exchange_id = (
        dialog_manager.dialog_data.get("exchange_id", None)
        or dialog_manager.start_data["exchange_id"]
    )

    if not exchange_id or not selected_date:
        await _event.answer("❌ Ошибка при обновлении даты", show_alert=True)
        return

    # Сохраняем выбранную дату для последующего использования
    dialog_manager.dialog_data["selected_date"] = selected_date.isoformat()

    # Переходим к вводу времени
    await dialog_manager.switch_to(Exchanges.edit_offer_date_time)


async def on_edit_date_time_input(
    message: Any,
    widget: Any,
    dialog_manager: DialogManager,
    text: str,
    **_kwargs,
) -> None:
    """Обработчик ввода нового времени для сделки после выбора даты.

    Args:
        message: Сообщение от пользователя
        widget: Виджет ввода текста
        dialog_manager: Менеджер диалога
        text: Введенный текст
    """
    import re
    from datetime import datetime

    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]

    exchange_id = (
        dialog_manager.dialog_data.get("exchange_id", None)
        or dialog_manager.start_data["exchange_id"]
    )

    if not exchange_id:
        await message.answer("❌ Ошибка: сделка не найдена")
        return

    # Валидация формата времени
    time_pattern = r"^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$"
    match = re.match(time_pattern, text.strip())

    if not match:
        await message.answer("❌ Неверный формат времени. Используй формат ЧЧ:ММ-ЧЧ:ММ")
        return

    start_hour, start_minute, end_hour, end_minute = map(int, match.groups())

    # Валидация времени
    if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
        await message.answer("❌ Часы должны быть от 0 до 23")
        return

    if not (0 <= start_minute <= 59 and 0 <= end_minute <= 59):
        await message.answer("❌ Минуты должны быть от 0 до 59")
        return

    if start_minute not in [0, 30] or end_minute not in [0, 30]:
        await message.answer("❌ Минуты могут быть только 00 или 30")
        return

    # Проверка корректности интервала
    start_total_minutes = start_hour * 60 + start_minute
    end_total_minutes = end_hour * 60 + end_minute

    if start_total_minutes >= end_total_minutes:
        await message.answer("❌ Время начала должно быть раньше времени окончания")
        return

    if end_total_minutes - start_total_minutes < 30:
        await message.answer("❌ Минимальная продолжительность смены: 30 минут")
        return

    try:
        # Получаем выбранную дату из dialog_data
        selected_date_str = dialog_manager.dialog_data.get("selected_date")
        if not selected_date_str:
            await message.answer("❌ Ошибка: дата не выбрана")
            return

        # Формируем новые времена с выбранной датой
        shift_date = datetime.fromisoformat(selected_date_str).date()
        start_time = datetime.combine(
            shift_date,
            datetime.min.time().replace(hour=start_hour, minute=start_minute),
        )
        end_time = datetime.combine(
            shift_date, datetime.min.time().replace(hour=end_hour, minute=end_minute)
        )

        # Обновляем и дату, и время одновременно
        await stp_repo.exchange.update_exchange_date(exchange_id, start_time, end_time)
        await message.answer("✅ Дата и время успешно обновлены")
        await dialog_manager.switch_to(Exchanges.my_detail)
    except Exception as e:
        logger.error(f"Error updating exchange date and time: {e}")
        await message.answer("❌ Ошибка при обновлении даты и времени")


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

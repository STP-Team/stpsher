"""События для биржи подмен."""

import logging
from datetime import datetime
from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import ChatEvent, DialogManager
from aiogram_dialog.widgets.kbd import Button, ManagedCalendar, ManagedCheckbox, Select
from stp_database import MainRequestsRepo

from tgbot.dialogs.states.common.exchanges import (
    ExchangeCreateBuy,
    ExchangeCreateSell,
    Exchanges,
)

logger = logging.getLogger(__name__)


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


async def finish_exchanges_dialog(
    _callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
) -> None:
    """Завершение диалога биржи.

    Args:
        _callback: Callback query от Telegrma
        _button: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.done()


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


async def on_exchange_buy(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
):
    """Обработчик покупки предложения."""
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
                "❌ Ты заблокирован от участия в бирже", show_alert=True
            )
            return

        # Получаем обмен
        exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
        if not exchange or exchange.status != "active":
            await callback.answer("❌ Предложение недоступно", show_alert=True)
            return

        # Покупаем обмен
        success = await stp_repo.exchange.buy_exchange(exchange_id, user_id)

        if success:
            await callback.answer(
                "✅ Смена успешно куплена! Свяжись с продавцом для уточнения деталей",
                show_alert=True,
            )
            dialog_manager.dialog_data.clear()
            await dialog_manager.switch_to(Exchanges.buy)
        else:
            await callback.answer(
                "❌ Не удалось купить смену. Попробуй позже.", show_alert=True
            )

    except Exception as e:
        logger.error(e)
        await callback.answer(
            "❌ Произошла ошибка при обработке запроса", show_alert=True
        )


async def on_exchange_sell(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
):
    """Обработчик покупки обмена или принятия запроса на покупку."""
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
                "❌ Ты заблокирован от участия в бирже", show_alert=True
            )
            return

        # Получаем обмен
        exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
        if not exchange or exchange.status != "active":
            await callback.answer("❌ Предложение недоступно", show_alert=True)
            return

        # Покупаем обмен
        success = await stp_repo.exchange.buy_exchange(exchange_id, user_id)

        if success:
            await callback.answer(
                "✅ Смена успешно куплена! Свяжись с продавцом для уточнения деталей",
                show_alert=True,
            )
            dialog_manager.dialog_data.clear()
            await dialog_manager.switch_to(Exchanges.buy)
        else:
            await callback.answer(
                "❌ Не удалось купить смену. Попробуй позже.", show_alert=True
            )

    except Exception as e:
        logger.error(e)
        await callback.answer(
            "❌ Произошла ошибка при обработке запроса", show_alert=True
        )


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
        success = await stp_repo.exchange.cancel_exchange(exchange_id, user_id)

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


async def on_my_exchange_selected(
    callback: CallbackQuery,
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
        await callback.answer("❌ Ошибка выбора обмена", show_alert=True)


async def on_exchange_type_selected(
    _callback: ChatEvent, _select: Select, dialog_manager: DialogManager, item_id: str
) -> None:
    """Обработчик выбора типа предложения.

    Args:
        _callback: Callback query от Telegram
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


async def on_private_change(
    _callback: CallbackQuery,
    widget: ManagedCheckbox,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Изменение приватности сделки.

    Args:
        _callback: Callback query от Telegram
        widget: Виджет чекбокса
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data.get("stp_repo")

    if dialog_manager.start_data:
        exchange_id = dialog_manager.start_data.get("exchange_id", None)
    else:
        exchange_id = dialog_manager.dialog_data.get("exchange_id", None)

    is_private = widget.is_checked()

    exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)

    if exchange.is_private == is_private:
        return

    if is_private:
        await stp_repo.exchange.set_private(exchange_id)
    else:
        await stp_repo.exchange.set_public(exchange_id)


async def on_restore_exchange(
    _callback: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
):
    """Отмена сделки.

    Args:
        _callback: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data.get("stp_repo")

    if dialog_manager.start_data:
        exchange_id = dialog_manager.start_data.get("exchange_id", None)
    else:
        exchange_id = dialog_manager.dialog_data.get("exchange_id", None)

    await stp_repo.exchange.activate_exchange(exchange_id)


async def on_cancel_exchange(
    _callback: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Отмена сделки.

    Args:
        _callback: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data.get("stp_repo")

    if dialog_manager.start_data:
        exchange_id = dialog_manager.start_data.get("exchange_id", None)
    else:
        exchange_id = dialog_manager.dialog_data.get("exchange_id", None)

    await stp_repo.exchange.cancel_exchange(exchange_id)


async def on_delete_exchange(
    _callback: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    **_kwargs,
):
    """Удаление сделки.

    Args:
        _callback: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data.get("stp_repo")

    if dialog_manager.start_data:
        exchange_id = dialog_manager.start_data.get("exchange_id", None)
    else:
        exchange_id = dialog_manager.dialog_data.get("exchange_id", None)

    await stp_repo.exchange.delete_exchange(exchange_id)
    await dialog_manager.switch_to(Exchanges.my)


async def on_set_paid(
    _callback: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Отметка сделки оплаченной.

    Args:
        _callback: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data.get("stp_repo")

    if dialog_manager.start_data:
        exchange_id = dialog_manager.start_data.get("exchange_id", None)
    else:
        exchange_id = dialog_manager.dialog_data.get("exchange_id", None)

    await stp_repo.exchange.mark_exchange_paid(exchange_id)


async def on_edit_offer_date(
    _callback: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик редактирования даты сделки.

    Args:
        _callback: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.switch_to(Exchanges.edit_offer_date)


async def on_edit_offer_price(
    _callback: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик редактирования цены сделки.

    Args:
        _callback: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.switch_to(Exchanges.edit_offer_price)


async def on_edit_offer_payment_timing(
    _callback: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик редактирования условий оплаты сделки.

    Args:
        _callback: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.switch_to(Exchanges.edit_offer_payment_timing)


async def on_edit_offer_comment(
    _callback: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик редактирования комментария сделки.

    Args:
        _callback: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.switch_to(Exchanges.edit_offer_comment)


async def on_edit_date_selected(
    _callback: CallbackQuery,
    _calendar: ManagedCalendar,
    dialog_manager: DialogManager,
    selected_date: datetime,
) -> None:
    """Обработчик выбора новой даты для сделки.

    Args:
        _callback: Callback query от Telegram
        _widget: Виджет календаря
        dialog_manager: Менеджер диалога
    """
    if dialog_manager.start_data:
        exchange_id = dialog_manager.start_data.get("exchange_id", None)
    else:
        exchange_id = dialog_manager.dialog_data.get("exchange_id", None)

    if not exchange_id or not selected_date:
        await _callback.answer("❌ Ошибка при обновлении даты", show_alert=True)
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

    if dialog_manager.start_data:
        exchange_id = dialog_manager.start_data.get("exchange_id", None)
    else:
        exchange_id = dialog_manager.dialog_data.get("exchange_id", None)

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

    if dialog_manager.start_data:
        exchange_id = dialog_manager.start_data.get("exchange_id", None)
    else:
        exchange_id = dialog_manager.dialog_data.get("exchange_id", None)

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
    _callback: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    item_id: str,
    **_kwargs,
) -> None:
    """Обработчик выбора условий оплаты.

    Args:
        _callback: Callback query от Telegram
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
    _callback: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик выбора даты оплаты.

    Args:
        _callback: Callback query от Telegram
        _widget: Виджет календаря
        dialog_manager: Менеджер диалога
    """
    payment_date = dialog_manager.dialog_data.get("selected_date")
    payment_type = dialog_manager.dialog_data.get("edit_payment_type", "on_date")

    await _update_payment_timing(dialog_manager, payment_type, payment_date)


async def _update_payment_timing(
    dialog_manager: DialogManager, payment_type: str, payment_date: str = None
):
    """Вспомогательная функция для обновления условий оплаты."""
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]

    if dialog_manager.start_data:
        exchange_id = dialog_manager.start_data.get("exchange_id", None)
    else:
        exchange_id = dialog_manager.dialog_data.get("exchange_id", None)

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

    if dialog_manager.start_data:
        exchange_id = dialog_manager.start_data.get("exchange_id", None)
    else:
        exchange_id = dialog_manager.dialog_data.get("exchange_id", None)

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

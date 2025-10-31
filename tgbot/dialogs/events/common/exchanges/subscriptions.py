"""События для подписок на биржу."""

import logging
from datetime import time
from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.kbd import Button, ManagedRadio, ManagedToggle, Select
from stp_database import Employee, MainRequestsRepo

from tgbot.dialogs.states.common.exchanges import ExchangesSub

logger = logging.getLogger(__name__)


async def start_subscriptions_dialog(
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
    # Проверяем откуда вызвана подписка (из buy или sell окна)
    current_state = dialog_manager.current_context().state
    sub_type = None

    if hasattr(current_state, "state") and current_state.state:
        state_name = current_state.state
        if "buy" in state_name:
            sub_type = (
                "sell"  # Если в окне покупки, подписываемся на продажи (чтобы покупать)
            )
        elif "sell" in state_name:
            sub_type = (
                "buy"  # Если в окне продажи, подписываемся на покупки (чтобы продавать)
            )

    await dialog_manager.start(
        ExchangesSub.menu,
        data={"auto_type": sub_type} if sub_type else None,
    )


async def finish_subscriptions_dialog(
    _callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
) -> None:
    """Завершение диалога биржи.

    Args:
        _callback: Callback query от Telegram
        _button: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.done()


async def on_subscription_selected(
    callback: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Обработчик выбора подписки для просмотра деталей.

    Args:
        callback: Callback query от Telegram
        _widget: Данные виджета Select
        dialog_manager: Менеджер диалога
        item_id: ID выбранной подписки
    """
    try:
        subscription_id = int(item_id)
        dialog_manager.dialog_data["subscription_id"] = subscription_id
        await dialog_manager.switch_to(ExchangesSub.sub_detail)
    except (ValueError, TypeError):
        await callback.answer("❌ Ошибка выбора подписки", show_alert=True)


async def on_create_subscription(
    _callback: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик начала создания новой подписки.

    Args:
        _callback: Callback query от Telegram
        _widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    # Очищаем данные диалога для новой подписки
    dialog_manager.dialog_data.clear()

    # Проверяем есть ли автоматический тип из стартовых данных
    start_data = dialog_manager.start_data or {}
    auto_type = start_data.get("auto_type")

    dialog_manager.dialog_data["auto_exchange_type"] = auto_type
    await dialog_manager.switch_to(ExchangesSub.create_criteria)


async def on_delete_subscription(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик удаления подписки.

    Args:
        callback: Callback query от Telegram
        widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    subscription_id = dialog_manager.dialog_data.get("subscription_id")

    if not subscription_id:
        await callback.answer("❌ Подписка не найдена", show_alert=True)
        return

    try:
        # Удаляем подписку
        success = await stp_repo.exchange.delete_subscription(subscription_id)

        if success:
            await callback.answer("✅ Подписка удалена", show_alert=True)
            dialog_manager.dialog_data.clear()
            await dialog_manager.switch_to(ExchangesSub.menu)
        else:
            await callback.answer("❌ Ошибка удаления подписки", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка удаления подписки {subscription_id}: {e}")
        await callback.answer("❌ Ошибка удаления подписки", show_alert=True)


async def on_toggle_subscription(
    callback: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик включения/отключения подписки.

    Args:
        callback: Callback query от Telegram
        _widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    subscription_id = dialog_manager.dialog_data.get("subscription_id")

    if not subscription_id:
        await callback.answer("❌ Подписка не найдена", show_alert=True)
        return

    try:
        # Получаем текущий статус и переключаем (пока заглушка)
        subscription = await stp_repo.exchange.get_subscription_by_id(subscription_id)
        new_status = not subscription.is_active

        # Обновляем статус
        success = await stp_repo.exchange.update_subscription(
            subscription_id, is_active=new_status
        )

        if success:
            status_text = "включена" if new_status else "отключена"
            await callback.answer(f"✅ Подписка {status_text}", show_alert=True)
        else:
            await callback.answer("❌ Ошибка изменения статуса", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка переключения статуса подписки {subscription_id}: {e}")
        await callback.answer("❌ Ошибка изменения статуса", show_alert=True)


async def on_criteria_next(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик перехода к следующему или предыдущему шагу настройки критериев.

    Args:
        callback: Callback query от Telegram
        widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    current_state = dialog_manager.current_context().state
    widget_id = widget.widget_id if hasattr(widget, "widget_id") else None

    # Определяем направление навигации по ID виджета
    is_back = widget_id == "back_step"

    if is_back:
        # Логика для возврата назад
        await _navigate_back(current_state, dialog_manager)
    else:
        # Логика для движения вперед
        await _navigate_forward(current_state, dialog_manager)


async def _navigate_forward(current_state, dialog_manager: DialogManager) -> None:
    """Навигация вперед по шагам создания подписки."""
    # Получаем выбранные критерии
    criteria_widget: ManagedToggle = dialog_manager.find("criteria_toggles")
    selected_criteria = criteria_widget.get_checked() if criteria_widget else []

    if current_state == ExchangesSub.create_criteria:
        if "price" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_price)
        elif "time" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_time)
        elif "days" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_date)
        else:
            await dialog_manager.switch_to(ExchangesSub.create_confirmation)
    elif current_state == ExchangesSub.create_price:
        if "time" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_time)
        elif "days" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_date)
        else:
            await dialog_manager.switch_to(ExchangesSub.create_confirmation)
    elif current_state == ExchangesSub.create_time:
        if "days" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_date)
        else:
            await dialog_manager.switch_to(ExchangesSub.create_confirmation)
    elif current_state == ExchangesSub.create_date:
        await dialog_manager.switch_to(ExchangesSub.create_confirmation)
    elif current_state == ExchangesSub.create_confirmation:
        # Возврат из подтверждения к последнему шагу настройки
        criteria_widget: ManagedToggle = dialog_manager.find("criteria_toggles")
        selected_criteria = criteria_widget.get_checked() if criteria_widget else []

        if "days" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_date)
        elif "time" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_time)
        elif "price" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_price)
        else:
            await dialog_manager.switch_to(ExchangesSub.create_criteria)


async def _navigate_back(current_state, dialog_manager: DialogManager) -> None:
    """Навигация назад по шагам создания подписки."""
    # Получаем выбранные критерии
    criteria_widget: ManagedToggle = dialog_manager.find("criteria_toggles")
    selected_criteria = criteria_widget.get_checked() if criteria_widget else []

    if current_state == ExchangesSub.create_price:
        await dialog_manager.switch_to(ExchangesSub.create_criteria)
    elif current_state == ExchangesSub.create_time:
        if "price" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_price)
        else:
            await dialog_manager.switch_to(ExchangesSub.create_criteria)
    elif current_state == ExchangesSub.create_date:
        if "time" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_time)
        elif "price" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_price)
        else:
            await dialog_manager.switch_to(ExchangesSub.create_criteria)
    elif current_state == ExchangesSub.create_confirmation:
        if "days" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_date)
        elif "time" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_time)
        elif "price" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_price)
        else:
            await dialog_manager.switch_to(ExchangesSub.create_criteria)


async def on_price_input(
    message: Message,
    _widget: ManagedTextInput,
    dialog_manager: DialogManager,
    data: int,
) -> None:
    """Обработчик ввода цены для подписки.

    Args:
        message: Сообщение от пользователя
        _widget: Данные виджета ManagedTextInput
        dialog_manager: Менеджер диалога
        data: Введенная цена
    """
    price_data = dialog_manager.dialog_data.setdefault("price_data", {})
    current_step = price_data.get("step", "min")

    if data < 0:
        await message.answer("❌ Цена не может быть отрицательной")
        return

    if current_step == "min":
        if data == 0:
            price_data["min_price"] = None
        else:
            price_data["min_price"] = data
        price_data["step"] = "max"
        await message.answer(
            f"✅ Минимальная цена: {data if data > 0 else 'не ограничена'}"
        )
    elif current_step == "max":
        if data == 0:
            price_data["max_price"] = None
        else:
            # Проверяем что максимальная цена больше минимальной
            min_price = price_data.get("min_price")
            if min_price and data <= min_price:
                await message.answer(
                    f"❌ Максимальная цена должна быть больше {min_price} р."
                )
                return
            price_data["max_price"] = data

        price_data["completed"] = True
        await message.answer(
            f"✅ Максимальная цена: {data if data > 0 else 'не ограничена'}"
        )


async def on_seller_selected(
    _callback: CallbackQuery,
    _widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Обработчик выбора конкретного продавца для подписки.

    Args:
        _callback: Callback query от Telegram
        _widget: Данные виджета Select
        dialog_manager: Менеджер диалога
        item_id: ID выбранного продавца
    """
    try:
        seller_id = int(item_id)
        dialog_manager.dialog_data["selected_seller_id"] = seller_id
    except (ValueError, TypeError):
        logger.error(f"Ошибка выбора продавца: неверный ID {item_id}")


async def on_confirm_subscription(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик подтверждения создания подписки.

    Args:
        callback: Callback query от Telegram
        widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user: Employee = dialog_manager.middleware_data["user"]

    try:
        # Собираем все данные подписки
        subscription_data = _collect_subscription_data(dialog_manager, user)

        # Создаем подписку
        subscription = await stp_repo.exchange.create_subscription(**subscription_data)
        subscription_id = subscription.id if subscription else None

        if subscription_id:
            await callback.answer("✅ Подписка создана успешно!", show_alert=True)
            dialog_manager.dialog_data.clear()
            await dialog_manager.switch_to(ExchangesSub.menu)
        else:
            await callback.answer("❌ Ошибка создания подписки", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка создания подписки для пользователя {user.user_id}: {e}")
        await callback.answer("❌ Ошибка создания подписки", show_alert=True)


def _collect_subscription_data(dialog_manager: DialogManager, user: Employee) -> dict:
    """Собирает все данные подписки для создания.

    Args:
        dialog_manager: Менеджер диалога
        user: Пользователь

    Returns:
        Словарь с данными подписки
    """
    # Основные данные
    auto_type = dialog_manager.dialog_data.get("auto_exchange_type")
    if auto_type:
        exchange_type = auto_type
    else:
        exchange_type_widget: ManagedRadio = dialog_manager.find("exchange_type")
        exchange_type = (
            exchange_type_widget.get_checked() if exchange_type_widget else "buy"
        )

    criteria_widget: ManagedToggle = dialog_manager.find("criteria_toggles")
    selected_criteria = criteria_widget.get_checked() if criteria_widget else []

    data = {
        "subscriber_id": user.user_id,
        "name": dialog_manager.dialog_data.get("subscription_name", "Моя подписка"),
        "exchange_type": exchange_type,
        "subscription_type": "custom" if selected_criteria else "all",
    }

    # Цена
    price_data = dialog_manager.dialog_data.get("price_data", {})
    if "price" in selected_criteria:
        data["min_price"] = price_data.get("min_price")
        data["max_price"] = price_data.get("max_price")

    # Время
    if "time" in selected_criteria:
        time_widget: ManagedRadio = dialog_manager.find("time_range")
        selected_time = time_widget.get_checked() if time_widget else None
        if selected_time:
            time_ranges = {
                "morning": (time(6, 0), time(12, 0)),
                "afternoon": (time(12, 0), time(18, 0)),
                "evening": (time(18, 0), time(23, 59)),
                "night": (time(0, 0), time(6, 0)),
                "work_hours": (time(8, 0), time(20, 0)),
            }
            if selected_time in time_ranges:
                data["start_time"] = time_ranges[selected_time][0]
                data["end_time"] = time_ranges[selected_time][1]

    # Дни недели
    if "days" in selected_criteria:
        days_widget: ManagedToggle = dialog_manager.find("days_of_week")
        selected_days = days_widget.get_checked() if days_widget else []
        if selected_days:
            # Преобразуем строки в числа
            data["days_of_week"] = [int(day) for day in selected_days]

    # Уведомления: всегда включены мгновенные уведомления о новых/отредактированных обменах
    data["notify_immediately"] = True
    data["notify_daily_digest"] = False
    data["notify_before_expire"] = False

    # Продавец (если выбран)
    if "seller" in selected_criteria:
        data["target_seller_id"] = dialog_manager.dialog_data.get("selected_seller_id")

    return data

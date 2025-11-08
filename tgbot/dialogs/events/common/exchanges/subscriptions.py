"""События для подписок на биржу."""

import logging
from datetime import time

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.kbd import (
    Button,
    ManagedCheckbox,
    ManagedRadio,
    ManagedToggle,
    Select,
)
from stp_database import Employee, ExchangeSubscription, MainRequestsRepo

from tgbot.dialogs.states.common.exchanges import ExchangesSub

logger = logging.getLogger(__name__)


async def start_subscriptions_dialog(
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
        data={"type": sub_type} if sub_type else None,
    )


async def finish_subscriptions_dialog(
    _event: CallbackQuery, _widget: Button, dialog_manager: DialogManager
) -> None:
    """Завершение диалога биржи.

    Args:
        _event: Callback query от Telegram
        _button: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.done()


async def on_subscription_selected(
    event: CallbackQuery,
    _widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Обработчик выбора подписки для просмотра деталей.

    Args:
        event: Callback query от Telegram
        _widget: Данные виджета Select
        dialog_manager: Менеджер диалога
        item_id: ID выбранной подписки
    """
    try:
        subscription_id = int(item_id)
        dialog_manager.dialog_data["subscription_id"] = subscription_id
        await dialog_manager.switch_to(ExchangesSub.sub_detail)
    except (ValueError, TypeError):
        await event.answer("❌ Ошибка выбора подписки", show_alert=True)


async def on_sub_status_click(
    _event: CallbackQuery, widget: ManagedCheckbox, dialog_manager: DialogManager
) -> None:
    """Изменение статуса подписки.

    Args:
        _event: Callback query от Telegram
        widget: Виджет чекбокса
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    subscription_id = (
        dialog_manager.dialog_data.get("subscription_id", None)
        or dialog_manager.start_data["subscription_id"]
    )

    subscription: ExchangeSubscription = await stp_repo.exchange.get_subscription_by_id(
        subscription_id
    )

    if subscription:
        await stp_repo.exchange.update_subscription(
            subscription_id, is_active=not widget.is_checked()
        )


async def on_create_subscription(
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик начала создания новой подписки.

    Args:
        _event: Callback query от Telegram
        _widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    # Очищаем данные диалога для новой подписки
    dialog_manager.dialog_data.clear()

    dialog_manager.dialog_data["type"] = dialog_manager.start_data["type"]
    await dialog_manager.switch_to(ExchangesSub.create_criteria)


async def on_delete_subscription(
    event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик удаления подписки.

    Args:
        event: Callback query от Telegram
        _widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    subscription_id = (
        dialog_manager.dialog_data.get("subscription_id", None)
        or dialog_manager.start_data["subscription_id"]
    )

    try:
        # Удаляем подписку
        success = await stp_repo.exchange.delete_subscription(subscription_id)

        if success:
            await event.answer("✅ Подписка удалена", show_alert=True)
            dialog_manager.dialog_data.clear()
            await dialog_manager.switch_to(ExchangesSub.menu)
        else:
            await event.answer("❌ Ошибка удаления подписки", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка удаления подписки {subscription_id}: {e}")
        await event.answer("❌ Ошибка удаления подписки", show_alert=True)


async def on_criteria_next(
    _event: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик перехода к следующему или предыдущему шагу настройки критериев.

    Args:
        _event: Callback query от Telegram
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
        elif "seller" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_seller)
        else:
            await dialog_manager.switch_to(ExchangesSub.create_confirmation)
    elif current_state == ExchangesSub.create_price:
        if "time" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_time)
        elif "days" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_date)
        elif "seller" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_seller)
        else:
            await dialog_manager.switch_to(ExchangesSub.create_confirmation)
    elif current_state == ExchangesSub.create_time:
        if "days" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_date)
        elif "seller" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_seller)
        else:
            await dialog_manager.switch_to(ExchangesSub.create_confirmation)
    elif current_state == ExchangesSub.create_date:
        if "seller" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_seller)
        else:
            await dialog_manager.switch_to(ExchangesSub.create_confirmation)
    elif (
        current_state == ExchangesSub.create_seller
        or current_state == ExchangesSub.create_seller_results
    ):
        await dialog_manager.switch_to(ExchangesSub.create_confirmation)
    elif current_state == ExchangesSub.create_confirmation:
        # Возврат из подтверждения к последнему шагу настройки
        if "seller" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_seller)
        elif "days" in selected_criteria:
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
    elif (
        current_state == ExchangesSub.create_seller
        or current_state == ExchangesSub.create_seller_results
    ):
        if "days" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_date)
        elif "time" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_time)
        elif "price" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_price)
        else:
            await dialog_manager.switch_to(ExchangesSub.create_criteria)
    elif current_state == ExchangesSub.create_confirmation:
        if "seller" in selected_criteria:
            await dialog_manager.switch_to(ExchangesSub.create_seller)
        elif "days" in selected_criteria:
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
    """Обработчик ввода минимальной цены в час для подписки.

    Args:
        message: Сообщение от пользователя
        _widget: Данные виджета ManagedTextInput
        dialog_manager: Менеджер диалога
        data: Введенная минимальная цена в час
    """
    if data < 0:
        await message.answer("❌ Цена не может быть отрицательной")
        return

    # Сохраняем только минимальную цену
    price_data = dialog_manager.dialog_data.setdefault("price_data", {})

    if data == 0:
        price_data["min_price"] = None
        await message.answer("✅ Минимальная цена: не ограничена")
    else:
        price_data["min_price"] = data
        await message.answer(f"✅ Минимальная цена: {data} ₽/час")

    price_data["completed"] = True

    # Автоматически переходим к следующему шагу
    await _navigate_forward(dialog_manager.current_context().state, dialog_manager)


async def on_seller_search_query(
    _message: Message,
    _widget: ManagedTextInput,
    dialog_manager: DialogManager,
    text: str,
) -> None:
    """Обработчик поискового запроса сотрудника для подписки.

    Args:
        _message: Сообщение пользователя
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
        text: Текст запроса
    """
    search_query = text.strip()

    if not search_query or len(search_query) < 2:
        return

    try:
        stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
        if not stp_repo:
            return

        # Поиск сотрудников
        found_users = await stp_repo.employee.search_users(search_query, limit=50)

        if not found_users:
            # Сохраняем поисковый запрос для отображения в окне "ничего не найдено"
            dialog_manager.dialog_data["seller_search_query"] = search_query
            dialog_manager.dialog_data["seller_search_results"] = []
            dialog_manager.dialog_data["seller_search_total"] = 0
            # Переходим к результатам поиска (пустым)
            await dialog_manager.switch_to(ExchangesSub.create_seller_results)
            return

        # Сортировка результатов
        sorted_users = sorted(
            found_users,
            key=lambda u: (
                search_query.lower() not in u.fullname.lower(),
                u.fullname,
            ),
        )

        # Сохраняем результаты поиска (используем user_id для foreign key)
        dialog_manager.dialog_data["seller_search_results"] = [
            (user.user_id, f"{user.fullname} ({user.position or 'Без должности'})")
            for user in sorted_users
        ]
        dialog_manager.dialog_data["seller_search_query"] = search_query
        dialog_manager.dialog_data["seller_search_total"] = len(sorted_users)

        # Переходим к результатам поиска
        await dialog_manager.switch_to(ExchangesSub.create_seller_results)

    except Exception as e:
        logger.error(f"Ошибка поиска сотрудника для подписки: {e}")


async def on_seller_selected(
    _event: CallbackQuery,
    _widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Обработчик выбора конкретного продавца для подписки.

    Args:
        _event: Callback query от Telegram
        _widget: Данные виджета Select
        dialog_manager: Менеджер диалога
        item_id: ID выбранного продавца
    """
    try:
        seller_user_id = int(item_id)
        dialog_manager.dialog_data["selected_seller_id"] = seller_user_id

        # Получаем информацию о выбранном сотруднике для отображения
        stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
        selected_employee = await stp_repo.employee.get_users(user_id=seller_user_id)

        if selected_employee:
            dialog_manager.dialog_data["selected_seller_name"] = (
                selected_employee.fullname
            )

        # Переходим к следующему шагу навигации
        await _navigate_forward(dialog_manager.current_context().state, dialog_manager)

    except (ValueError, TypeError):
        logger.error(f"Ошибка выбора продавца: неверный ID {item_id}")
    except Exception as e:
        logger.error(f"Ошибка при выборе продавца: {e}")


async def on_confirm_subscription(
    event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик подтверждения создания подписки.

    Args:
        event: Callback query от Telegram
        _widget: Данные виджета Button
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
            await event.answer("✅ Подписка создана успешно!", show_alert=True)
            dialog_manager.dialog_data.clear()
            await dialog_manager.switch_to(ExchangesSub.menu)
        else:
            await event.answer("❌ Ошибка создания подписки", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка создания подписки для пользователя {user.user_id}: {e}")
        await event.answer("❌ Ошибка создания подписки", show_alert=True)


def _collect_subscription_data(dialog_manager: DialogManager, user: Employee) -> dict:
    """Собирает все данные подписки для создания.

    Args:
        dialog_manager: Менеджер диалога
        user: Пользователь

    Returns:
        Словарь с данными подписки
    """
    exchange_type: ManagedRadio = dialog_manager.dialog_data.get("type")

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
        # Добавляем поддержку max_price если есть в данных
        if "max_price" in price_data:
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
            # Преобразуем строки в числа для JSON поля
            data["days_of_week"] = [int(day) for day in selected_days]

    # Продавец (если выбран)
    if "seller" in selected_criteria:
        data["target_seller_id"] = dialog_manager.dialog_data.get("selected_seller_id")

    # Даты (новые поля в схеме)
    date_data = dialog_manager.dialog_data.get("date_data", {})
    if "start_date" in date_data:
        data["start_date"] = date_data["start_date"]
    if "end_date" in date_data:
        data["end_date"] = date_data["end_date"]

    # Подразделения (новое поле target_divisions)
    divisions_data = dialog_manager.dialog_data.get("target_divisions")
    if divisions_data:
        # Preserve original strings without unnecessary conversion
        if isinstance(divisions_data, list):
            data["target_divisions"] = divisions_data
        elif isinstance(divisions_data, str):
            data["target_divisions"] = [divisions_data]
        else:
            data["target_divisions"] = divisions_data

    return data

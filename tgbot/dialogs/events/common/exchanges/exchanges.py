"""События для биржи подмен."""

from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import ChatEvent, DialogManager
from aiogram_dialog.widgets.kbd import Button, ManagedCheckbox, Select
from stp_database import MainRequestsRepo

from tgbot.dialogs.states.common.exchanges import (
    ExchangeCreateBuy,
    ExchangeCreateSell,
    Exchanges,
)


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
    await dialog_manager.done()


async def on_private_change(
    _callback: CallbackQuery,
    widget: ManagedCheckbox,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data.get("stp_repo")
    exchange_id = dialog_manager.dialog_data.get("exchange_id")

    is_private = widget.is_checked()

    exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)

    if exchange.is_private == is_private:
        return

    if is_private:
        await stp_repo.exchange.set_private(exchange_id)
    else:
        await stp_repo.exchange.set_public(exchange_id)


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
                "❌ Вы заблокированы от участия в бирже подмен", show_alert=True
            )
            return

        # Получаем обмен
        exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
        if not exchange or exchange.status != "active":
            await callback.answer("❌ Обмен недоступен", show_alert=True)
            return

        # Определяем контекст: откуда пришли (buy_detail или sell_detail)
        current_state = dialog_manager.current_stack().state

        if current_state.state == "buy_detail":
            # Контекст: покупка sell-предложения
            # Проверяем, что это не собственное предложение
            if exchange.seller_id == user_id:
                await callback.answer(
                    "❌ Нельзя купить собственное предложение", show_alert=True
                )
                return

            # Покупаем обмен
            success = await stp_repo.exchange.buy_exchange(exchange_id, user_id)

            if success:
                await callback.answer(
                    "✅ Смена успешно куплена! Свяжитесь с продавцом для деталей.",
                    show_alert=True,
                )
                dialog_manager.dialog_data.clear()
                await dialog_manager.switch_to(Exchanges.buy)
            else:
                await callback.answer(
                    "❌ Не удалось купить смену. Попробуйте позже.", show_alert=True
                )

        elif current_state.state == "sell_detail":
            # Контекст: принятие buy-запроса
            # Проверяем, что это buy-запрос
            if exchange.type != "buy":
                await callback.answer("❌ Неверный тип запроса", show_alert=True)
                return

            # Проверяем, что это не собственный запрос
            if exchange.seller_id == user_id:  # В buy-запросе seller_id это buyer_id
                await callback.answer(
                    "❌ Нельзя принять собственный запрос", show_alert=True
                )
                return

            # Принимаем buy-запрос (продаем нашу смену)
            success = await stp_repo.exchange.buy_exchange(exchange_id, user_id)

            if success:
                await callback.answer(
                    "✅ Смена успешно продана! Свяжитесь с покупателем для деталей.",
                    show_alert=True,
                )
                dialog_manager.dialog_data.clear()
                await dialog_manager.switch_to(Exchanges.sell)
            else:
                await callback.answer(
                    "❌ Не удалось продать смену. Попробуйте позже.", show_alert=True
                )

    except Exception:
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

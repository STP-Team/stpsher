"""События для биржи подмен."""

from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, ManagedCheckbox
from stp_database import MainRequestsRepo

from tgbot.dialogs.states.common.exchanges import Exchanges


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

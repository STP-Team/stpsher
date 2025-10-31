"""Обработчики истории баланса сотрудников."""

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Select
from stp_database import MainRequestsRepo

from tgbot.dialogs.states.common.game import Game
from tgbot.misc.helpers import strftime_date


async def on_transaction_click(
    event: CallbackQuery,
    _widget: Select,
    dialog_manager: DialogManager,
    item_id,
    **_kwargs,
) -> None:
    """Переход к детальному просмотру информации о выбранной транзакции.

    Args:
        callback: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
        item_id: Идентификатор выбранной транзакции
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]

    try:
        transaction = await stp_repo.transaction.get_transaction(item_id)
    except Exception as e:
        print(e)
        await event.answer(
            "❌ Ошибка получения информации о транзакции", show_alert=True
        )
        return

    if not transaction:
        await event.answer("❌ Транзакция не найдена", show_alert=True)
        return

    # Сохраняем информацию о выбранной транзакции в dialog_data
    dialog_manager.dialog_data["selected_transaction"] = {
        "id": transaction.id,
        "amount": transaction.amount,
        "type": transaction.type,
        "source_type": transaction.source_type,
        "source_id": transaction.source_id,
        "comment": transaction.comment or "",
        "created_at": transaction.created_at.strftime(strftime_date),
    }

    # Переходим к окну детального просмотра транзакции
    await dialog_manager.switch_to(Game.history_details)

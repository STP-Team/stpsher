"""Обработчики истории баланса сотрудников."""

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Select

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.dialogs.states.user import UserSG


async def on_transaction_click(
    callback: CallbackQuery,
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
        await callback.answer(
            "❌ Ошибка получения информации о транзакции", show_alert=True
        )
        return

    if not transaction:
        await callback.answer("❌ Транзакция не найдена", show_alert=True)
        return

    # Сохраняем информацию о выбранной транзакции в dialog_data
    dialog_manager.dialog_data["selected_transaction"] = {
        "id": transaction.id,
        "amount": transaction.amount,
        "type": transaction.type,
        "source_type": transaction.source_type,
        "source_id": transaction.source_id,
        "comment": transaction.comment or "",
        "created_at": transaction.created_at.strftime("%d.%m.%Y в %H:%M"),
    }

    # Переходим к окну детального просмотра транзакции
    await dialog_manager.switch_to(UserSG.game_history_detail)

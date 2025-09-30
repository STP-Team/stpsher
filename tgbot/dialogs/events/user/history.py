from aiogram_dialog import DialogManager

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.misc.states.dialogs.user import UserSG


async def on_transaction_click(
    callback, widget, dialog_manager: DialogManager, item_id, **kwargs
):
    """
    Обработчик нажатия на транзакцию - переход к детальному просмотру
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

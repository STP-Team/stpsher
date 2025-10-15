"""Фильтры истории баланса пользователя."""

from aiogram_dialog import DialogManager

from tgbot.dialogs.getters.common.game.history import history_getter


async def history_filter_getter(dialog_manager: DialogManager, **kwargs):
    """Фильтрует транзакции в зависимости от выбранных фильтров (тип и источник).

    Доступные фильтры:
    - Тип транзакции (доход/расход)
    - Источник транзакции (достижение, покупка и пр.)

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь отфильтрованных транзакций истории баланса
    """
    base_data = await history_getter(**kwargs)

    # Проверяем текущий выбор фильтров
    type_filter = dialog_manager.find("history_type_filter").get_checked()
    source_filter = dialog_manager.find("history_source_filter").get_checked()

    transactions = base_data["history_products"]
    total_transactions = base_data["total_transactions"]

    # Применяем фильтр по типу транзакции
    if type_filter == "earn":
        filtered_transactions = [
            t
            for t in transactions
            if t[6] == "earn"  # t[6] это type
        ]
    elif type_filter == "spend":
        filtered_transactions = [
            t
            for t in transactions
            if t[6] == "spend"  # t[6] это type
        ]
    else:  # "all"
        filtered_transactions = transactions

    # Применяем фильтр по источнику транзакции
    if source_filter != "all":
        filtered_transactions = [
            t
            for t in filtered_transactions
            if t[7] == source_filter  # t[7] это source_type
        ]

    return {
        "history_products": filtered_transactions,
        "total_transactions": total_transactions,
        "filtered_count": len(filtered_transactions),
        "history_type_filter": type_filter,
        "history_source_filter": source_filter,
    }

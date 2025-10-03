from aiogram_dialog import DialogManager

from tgbot.dialogs.getters.user.game.history import history_getter


async def history_filter_getter(dialog_manager: DialogManager, **kwargs):
    """Фильтрует транзакции в зависимости от выбранных радио-фильтров (тип и источник)"""
    base_data = await history_getter(**kwargs)

    # Проверяем текущий выбор фильтров (стандартно на 'all')
    type_filter = dialog_manager.dialog_data.get("history_type_filter", "all")
    source_filter = dialog_manager.dialog_data.get("history_source_filter", "all")

    # Устанавливаем стандартные фильтры если не установлено иное
    if "history_type_filter" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["history_type_filter"] = "all"
    if "history_source_filter" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["history_source_filter"] = "all"

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

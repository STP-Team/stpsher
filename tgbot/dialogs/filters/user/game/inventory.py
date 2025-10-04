"""Фильтры предметов инвентаря пользователя."""

from aiogram_dialog import DialogManager

from tgbot.dialogs.getters.common.game.inventory import inventory_getter


async def inventory_filter_getter(dialog_manager: DialogManager, **kwargs):
    """Фильтрует предметы в инвентаре в зависимости от выбранных фильтров.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь отфильтрованных предметов инвентаря
    """
    base_data = await inventory_getter(**kwargs)

    # Проверяем текущий выбор фильтра (стандартно на 'all')
    filter_type = dialog_manager.dialog_data.get("inventory_filter", "all")

    # Устанавливаем стандартный фильтр если не установлено иное
    if "inventory_filter" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["inventory_filter"] = "all"

    products = base_data["products"]
    total_bought = base_data["total_bought"]

    if filter_type != "all":
        # Фильтруем предметы по статусу
        filtered_products = [
            p
            for p in products
            if p[5] == filter_type  # p[5] это status
        ]
    else:
        filtered_products = products

    return {
        "products": filtered_products,
        "total_bought": total_bought,
        "inventory_filter": filter_type,
    }

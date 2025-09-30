from tgbot.dialogs.getters.user.game.inventory import inventory_getter


async def inventory_filter_getter(**kwargs):
    """
    Фильтрует предметы в инвентаре в зависимости от выбранного радио-фильтра
    """
    base_data = await inventory_getter(**kwargs)
    dialog_manager = kwargs.get("dialog_manager")

    # Проверяем текущий выбор фильтра (стандартно на 'all')
    filter_type = dialog_manager.dialog_data.get("purchases_filter", "all")

    # Устанавливаем стандартный фильтр если не установлено иное
    if "purchases_filter" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["purchases_filter"] = "all"

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

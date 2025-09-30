async def on_filter_change(callback, widget, dialog_manager, item_id, **kwargs):
    """
    Обработчик нажатия на фильтр
    """
    if widget.widget_id == "shop_filter":
        dialog_manager.dialog_data["product_filter"] = item_id
    elif widget.widget_id == "inventory_filter":
        dialog_manager.dialog_data["purchases_filter"] = item_id
    elif widget.widget_id == "achievement_position_filter":
        dialog_manager.dialog_data["achievement_position_filter"] = item_id
    elif widget.widget_id == "achievement_division_filter":
        dialog_manager.dialog_data["achievement_division_filter"] = item_id
    elif widget.widget_id == "achievement_period_filter":
        dialog_manager.dialog_data["achievement_period_filter"] = item_id
    elif widget.widget_id == "history_type_filter":
        dialog_manager.dialog_data["history_type_filter"] = item_id
    elif widget.widget_id == "history_source_filter":
        dialog_manager.dialog_data["history_source_filter"] = item_id
    elif widget.widget_id == "search_divisions":
        dialog_manager.dialog_data["search_divisions"] = item_id
    elif widget.widget_id == "search_roles":
        dialog_manager.dialog_data["search_roles"] = item_id
    await callback.answer()

from tgbot.misc.states.user.main import UserSG


async def on_user_select(callback, widget, dialog_manager, item_id, **kwargs):
    """
    Обработчик выбора пользователя из списка поиска
    """
    dialog_manager.dialog_data["selected_user_id"] = item_id
    await dialog_manager.switch_to(UserSG.search_result)

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, Radio

from tgbot.misc.states.user.main import UserSG


async def on_mode_select(
    callback: CallbackQuery, radio: Radio, dialog_manager: DialogManager, item_id: str
):
    current_state = dialog_manager.current_context().state

    if item_id == "compact":
        if current_state == UserSG.schedule_my_detailed:
            await dialog_manager.switch_to(UserSG.schedule_my)
    elif item_id == "detailed":
        if current_state == UserSG.schedule_my:
            await dialog_manager.switch_to(UserSG.schedule_my_detailed)


async def switch_to_detailed(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    current_state = dialog_manager.current_context().state
    if current_state == UserSG.schedule_my:
        await dialog_manager.switch_to(UserSG.schedule_my_detailed)
    else:
        await dialog_manager.switch_to(UserSG.schedule_my)

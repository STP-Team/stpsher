from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Button
from stp_database import Employee

from tgbot.dialogs.states.admin import AdminSG
from tgbot.dialogs.states.gok import GokSG
from tgbot.dialogs.states.head import HeadSG
from tgbot.dialogs.states.mip import MipSG
from tgbot.dialogs.states.root import RootSG
from tgbot.dialogs.states.user import UserSG


async def close_all_dialogs(
    _callback: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик перехода в главное меню.

    Args:
        _callback: Callback query от Telegram
        _widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    user: Employee = dialog_manager.middleware_data["user"]

    # Маппинг ролей на состояния главного меню
    role_menu_mapping = {
        "1": UserSG.menu,
        "2": HeadSG.menu,
        "3": UserSG.menu,
        "4": AdminSG.menu,
        "5": GokSG.menu,
        "6": MipSG.menu,
        "10": RootSG.menu,
    }

    menu_state = role_menu_mapping.get(str(user.role), UserSG.menu)
    await dialog_manager.start(menu_state, mode=StartMode.RESET_STACK)

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.api.exceptions import NoContextError

from infrastructure.database.models import Employee
from tgbot.dialogs.states.admin import AdminSG
from tgbot.filters.role import AdminFilter

logger = logging.getLogger(__name__)

admin_router = Router()
admin_router.message.filter(F.chat.type == "private", AdminFilter())
admin_router.callback_query.filter(F.message.chat.type == "private", AdminFilter())


@admin_router.message(CommandStart())
async def admin_start(
    message: Message, user: Employee, dialog_manager: DialogManager
) -> None:
    """Запуск/сброс состояния диалога для специалистов и дежурных.

    Запускает авторизацию в случае ее отсутствия у пользователя.

    Args:
        message: Сообщение пользователя
        user: Экземпляр пользователя с моделью Employee
        dialog_manager: Менеджер диалога
    """
    try:
        await dialog_manager.done()
    except NoContextError:
        pass

    await dialog_manager.start(AdminSG.menu, mode=StartMode.RESET_STACK)

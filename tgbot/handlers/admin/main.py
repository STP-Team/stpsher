"""Запуск диалога для администраторов."""

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.api.exceptions import NoContextError
from stp_database import Employee

from tgbot.dialogs.states.admin import AdminSG
from tgbot.filters.role import AdminFilter
from tgbot.services.event_logger import EventLogger

logger = logging.getLogger(__name__)

admin_router = Router()
admin_router.message.filter(F.chat.type == "private", AdminFilter())
admin_router.callback_query.filter(F.message.chat.type == "private", AdminFilter())


@admin_router.message(CommandStart())
async def admin_start(
    _message: Message,
    user: Employee,
    dialog_manager: DialogManager,
    event_logger: EventLogger,
):
    """Запуск/сброс состояния диалога для руководителей.

    Args:
        user: Экземпляр пользователя с моделью Employee
        _message: Сообщение пользователя
        dialog_manager: Менеджер диалога
        event_logger: Логгер событий
    """
    await event_logger.log_bot_start(user.user_id)

    try:
        await dialog_manager.done()
    except NoContextError:
        pass

    await dialog_manager.start(AdminSG.menu, mode=StartMode.RESET_STACK)

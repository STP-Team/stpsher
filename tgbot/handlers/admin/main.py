"""Запуск диалога для администраторов."""

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.api.exceptions import NoContextError

from tgbot.dialogs.states.admin import AdminSG
from tgbot.filters.role import AdminFilter

logger = logging.getLogger(__name__)

admin_router = Router()
admin_router.message.filter(F.chat.type == "private", AdminFilter())
admin_router.callback_query.filter(F.message.chat.type == "private", AdminFilter())


@admin_router.message(CommandStart())
async def admin_start(
    _message: Message,
    dialog_manager: DialogManager,
):
    """Запуск/сброс состояния диалога для руководителей.

    Args:
        _message: Сообщение пользователя
        dialog_manager: Менеджер диалога
    """
    try:
        await dialog_manager.done()
    except NoContextError:
        pass

    await dialog_manager.start(AdminSG.menu, mode=StartMode.RESET_STACK)

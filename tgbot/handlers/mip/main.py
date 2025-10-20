"""Запуск диалога для МИП."""

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.api.exceptions import NoContextError
from stp_database import Employee

from tgbot.dialogs.states.mip import MipSG
from tgbot.filters.role import MipFilter
from tgbot.services.event_logger import EventLogger

mip_router = Router()
mip_router.message.filter(F.chat.type == "private", MipFilter())
mip_router.callback_query.filter(F.message.chat.type == "private", MipFilter())


@mip_router.message(CommandStart())
async def mip_start(
    _message: Message,
    user: Employee,
    dialog_manager: DialogManager,
    event_logger: EventLogger,
):
    """Запуск/сброс состояния диалога для МИП.

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

    await dialog_manager.start(MipSG.menu, mode=StartMode.RESET_STACK)

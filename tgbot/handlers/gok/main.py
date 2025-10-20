"""Запуск диалога для ГОК."""

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.api.exceptions import NoContextError
from stp_database import Employee

from tgbot.dialogs.states.gok import GokSG
from tgbot.filters.role import GokFilter
from tgbot.services.event_logger import EventLogger

gok_router = Router()
gok_router.message.filter(F.chat.type == "private", GokFilter())
gok_router.callback_query.filter(F.message.chat.type == "private", GokFilter())


@gok_router.message(CommandStart())
async def gok_start(
    _message: Message,
    user: Employee,
    dialog_manager: DialogManager,
    event_logger: EventLogger,
):
    """Запуск/сброс состояния диалога для ГОК.

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

    await dialog_manager.start(GokSG.menu, mode=StartMode.RESET_STACK)

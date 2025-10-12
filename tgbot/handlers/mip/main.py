"""Запуск диалога для МИП."""

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.api.exceptions import NoContextError

from tgbot.dialogs.states.mip import MipSG
from tgbot.filters.role import MipFilter

mip_router = Router()
mip_router.message.filter(F.chat.type == "private", MipFilter())
mip_router.callback_query.filter(F.message.chat.type == "private", MipFilter())


@mip_router.message(CommandStart())
async def mip_start(_message: Message, dialog_manager: DialogManager):
    """Запуск/сброс состояния диалога для МИП.

    Args:
        _message: Сообщение пользователя
        dialog_manager: Менеджер диалога
    """
    try:
        await dialog_manager.done()
    except NoContextError:
        pass

    await dialog_manager.start(MipSG.menu, mode=StartMode.RESET_STACK)

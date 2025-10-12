"""Запуск диалога для руководителей."""

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.api.exceptions import NoContextError

from tgbot.dialogs.states.heads.head import HeadSG
from tgbot.filters.role import HeadFilter

head_router = Router()
head_router.message.filter(F.chat.type == "private", HeadFilter())
head_router.callback_query.filter(F.message.chat.type == "private", HeadFilter())


@head_router.message(CommandStart())
async def head_start(
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

    await dialog_manager.start(HeadSG.menu, mode=StartMode.RESET_STACK)

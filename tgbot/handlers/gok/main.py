from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.api.exceptions import NoContextError

from tgbot.dialogs.states.gok import GokSG
from tgbot.filters.role import GokFilter

gok_router = Router()
gok_router.message.filter(F.chat.type == "private", GokFilter())
gok_router.callback_query.filter(F.message.chat.type == "private", GokFilter())


@gok_router.message(CommandStart())
async def gok_start(_message: Message, dialog_manager: DialogManager):
    """Запуск/сброс состояния диалога для ГОК.

    Args:
        _message: Сообщение пользователя
        dialog_manager: Менеджер диалога
    """
    try:
        await dialog_manager.done()
    except NoContextError:
        pass

    await dialog_manager.start(GokSG.menu, mode=StartMode.RESET_STACK)

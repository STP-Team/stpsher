from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.api.exceptions import NoContextError

from tgbot.filters.role import RootFilter
from tgbot.misc.states.dialogs.root import RootSG

root_router = Router()
root_router.message.filter(F.chat.type == "private", RootFilter())
root_router.callback_query.filter(F.message.chat.type == "private", RootFilter())


@root_router.message(CommandStart())
async def root_start(message: Message, dialog_manager: DialogManager):
    try:
        await dialog_manager.done()
    except NoContextError:
        pass

    await dialog_manager.start(RootSG.menu, mode=StartMode.RESET_STACK)

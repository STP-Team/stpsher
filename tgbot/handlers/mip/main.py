import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.api.exceptions import NoContextError

from infrastructure.database.models import Employee
from tgbot.filters.role import MipFilter
from tgbot.misc.states.dialogs.mip import MipSG

logger = logging.getLogger(__name__)

mip_router = Router()
mip_router.message.filter(F.chat.type == "private")
mip_router.callback_query.filter(F.message.chat.type == "private", MipFilter())


@mip_router.message(CommandStart())
async def mip_start(message: Message, user: Employee, dialog_manager: DialogManager):
    try:
        await dialog_manager.done()
    except NoContextError:
        pass

    await dialog_manager.start(MipSG.menu, mode=StartMode.RESET_STACK)

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from infrastructure.database.models import User
from tgbot.filters.role import RootFilter

admin_router = Router()
admin_router.message.filter(RootFilter())


@admin_router.message(CommandStart())
async def admin_start(message: Message, user: User):
    await message.reply(f"Привет, админ {user.fullname}!")

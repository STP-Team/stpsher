from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from infrastructure.database.models import Employee
from tgbot.filters.role import RootFilter

admin_router = Router()
admin_router.message.filter(RootFilter())


@admin_router.message(CommandStart())
async def admin_start(message: Message, user: Employee):
    await message.reply(f"Привет, админ {user.fullname}!")

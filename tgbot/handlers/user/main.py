from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from infrastructure.database.models import User

user_router = Router()


@user_router.message(CommandStart())
async def user_start(message: Message, user: User):
    await message.reply(f"Привет, {user.FIO}!")

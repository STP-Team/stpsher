from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from tgbot.filters.group import GroupAdminFilter
from tgbot.keyboards.group.settings import group_settings_keyboard

group_settings_router = Router()
group_settings_router.message.filter(F.chat.type.in_(("group", "supergroup")))


@group_settings_router.message(Command("settings"), GroupAdminFilter())
async def group_settings(message: Message):
    """Handle /settings command for group admins."""
    await message.answer(
        "<b>⚙️ Настройки группы</b>\n\nВыбери нужную настройку:",
        reply_markup=group_settings_keyboard(message.chat.id),
    )


@group_settings_router.message(Command("settings"))
async def group_settings_non_admin(message: Message):
    """Handle /settings command for non-admin users."""
    await message.answer(
        "Только администраторы группы могут использовать эту команду :("
    )

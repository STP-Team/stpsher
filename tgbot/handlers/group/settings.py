from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.deep_linking import create_start_link

from tgbot.filters.group import GroupAdminFilter

group_settings_router = Router()
group_settings_router.message.filter(F.chat.type.in_(("group", "supergroup")))


@group_settings_router.message(Command("settings"), GroupAdminFilter())
async def group_settings(message: Message):
    """Handle /settings command for group admins."""
    settings_deeplink = await create_start_link(
        message.bot, payload=f"group_{message.chat.id}", encode=True
    )
    await message.answer(
        f"""<b>⚙️ Настройки группы</b>

Для настройки группы нажми <a href='{settings_deeplink}'>сюда</a>""",
    )


@group_settings_router.message(Command("settings"))
async def group_settings_non_admin(message: Message):
    """Handle /settings command for non-admin users."""
    await message.reply(
        "Только администраторы группы могут использовать эту команду :("
    )

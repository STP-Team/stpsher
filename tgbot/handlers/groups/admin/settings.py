from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.deep_linking import create_start_link

from tgbot.filters.group import GroupAdminFilter

group_settings_router = Router()
group_settings_router.message.filter(F.chat.type.in_(("groups", "supergroup")))


@group_settings_router.message(Command("settings"), GroupAdminFilter())
async def group_settings(message: Message) -> None:
    """Обработчик команды /settings в группе для администраторов.

    Args:
        message: Сообщение от пользователя
    """
    settings_deeplink = await create_start_link(
        message.bot, payload=f"group_{message.chat.id}", encode=True
    )

    await message.answer(
        f"""<b>⚙️ Настройки группы</b>

Для настройки группы нажми <a href='{settings_deeplink}'>сюда</a>""",
    )


@group_settings_router.message(Command("settings"))
async def group_settings_non_admin(message: Message) -> None:
    """Обработчик команды /settings в группе для обычных пользователей.

    Args:
        message: Сообщение от пользователя
    """
    await message.reply(
        "Только администраторы группы могут использовать эту команду :("
    )

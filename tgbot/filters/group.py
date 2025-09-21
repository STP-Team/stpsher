from aiogram import Bot
from aiogram.filters import BaseFilter
from aiogram.types import ChatMember, Message


class GroupAdminFilter(BaseFilter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        """Проверка является ли пользователь администратором группы."""
        if message.chat.type not in ["group", "supergroup"]:
            return False

        member: ChatMember = await bot.get_chat_member(
            chat_id=message.chat.id, user_id=message.from_user.id
        )
        return member.status in ["administrator", "creator"]

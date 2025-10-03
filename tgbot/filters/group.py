"""Групповые фильтры."""

from aiogram import Bot
from aiogram.filters import BaseFilter
from aiogram.types import ChatMember, Message


class GroupAdminFilter(BaseFilter):
    """Фильтр проверки является ли пользователь администратором группы.

    Проверяет статус пользователя в чате и пропускает сообщения только
    от администраторов и создателей групп/супергрупп.
    """

    async def __call__(self, message: Message, bot: Bot) -> bool:
        """Проверяет является ли отправитель сообщения администратором группы.

        Args:
            message: Входящее сообщение из чата.
            bot: Экземпляр бота для API запросов.

        Returns:
            True если пользователь является администратором или создателем,
            False в остальных случаях (включая приватные чаты).
        """
        if message.chat.type not in ["group", "supergroup"]:
            return False

        member: ChatMember = await bot.get_chat_member(
            chat_id=message.chat.id, user_id=message.from_user.id
        )
        return member.status in ["administrator", "creator"]

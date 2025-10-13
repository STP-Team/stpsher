"""Фильтры для диплинков."""

import re

from aiogram.filters import BaseFilter, CommandObject
from aiogram.types import Message
from aiogram.utils.payload import decode_payload


class DeepLinkRegexFilter(BaseFilter):
    """Фильтр проверки deep-ссылок по регулярному выражению.

    Извлекает payload из deep-ссылки и проверяет соответствие заданному паттерну.
    """

    def __init__(self, pattern: str):
        """Инициализирует фильтр с заданным регулярным выражением.

        Args:
            pattern: Регулярное выражение для проверки payload.
        """
        self.pattern = re.compile(pattern)

    async def __call__(
        self, message: Message, command: CommandObject | None = None
    ) -> bool:
        """Проверяет соответствие payload deep-ссылки регулярному выражению.

        Args:
            message: Входящее сообщение.
            command: Объект команды с аргументами deep-ссылки.

        Returns:
            True если payload соответствует паттерну, False в противном случае.
        """
        if not command or not command.args:
            return False
        payload = decode_payload(command.args)
        return bool(self.pattern.match(payload))

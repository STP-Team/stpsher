import re

from aiogram.filters import BaseFilter, CommandObject
from aiogram.types import Message
from aiogram.utils.payload import decode_payload


class DeepLinkRegexFilter(BaseFilter):
    def __init__(self, pattern: str):
        self.pattern = re.compile(pattern)

    async def __call__(
        self, message: Message, command: CommandObject | None = None
    ) -> bool:
        if not command or not command.args:
            return False
        payload = decode_payload(command.args)
        return bool(self.pattern.match(payload))

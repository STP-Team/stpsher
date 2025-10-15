"""Middleware для доступа к конфигурации."""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message


class ConfigMiddleware(BaseMiddleware):
    """Middleware для доступа к конфигурации."""

    def __init__(self, config) -> None:
        """Инициализация middleware с конфигом.

        Args:
            config: Файл конфигурации
        """
        self.config = config

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        data["config"] = self.config
        return await handler(event, data)

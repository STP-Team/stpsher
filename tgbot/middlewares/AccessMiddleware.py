"""Middleware для операций с пользователями."""

import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, InlineQuery, Message
from stp_database.models.STP import Employee

logger = logging.getLogger(__name__)


class AccessMiddleware(BaseMiddleware):
    """Middleware, отвечающий за доступ к системам."""

    async def __call__(
        self,
        handler: Callable[
            [Union[Message, CallbackQuery, InlineQuery], Dict[str, Any]], Awaitable[Any]
        ],
        event: Union[Message, CallbackQuery, InlineQuery],
        data: Dict[str, Any],
    ) -> Any:
        user: Employee = data.get("user")

        if user and user.access is False:
            return None

        # Продолжаем к следующему middleware/обработчику
        result = await handler(event, data)
        return result

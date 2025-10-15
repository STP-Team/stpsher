"""Middleware для операций с пользователями."""

import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, InlineQuery, Message
from stp_database import Employee, MainRequestsRepo

from tgbot.services.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class UsersMiddleware(BaseMiddleware):
    """Middleware, отвечающий за контроль пользователей."""

    async def __call__(
        self,
        handler: Callable[
            [Union[Message, CallbackQuery, InlineQuery], Dict[str, Any]], Awaitable[Any]
        ],
        event: Union[Message, CallbackQuery, InlineQuery],
        data: Dict[str, Any],
    ) -> Any:
        user: Employee = data.get("user")
        stp_repo: MainRequestsRepo = data.get("stp_repo")

        if user:
            await self._update_username(user, event, stp_repo)

        # Продолжаем к следующему middleware/обработчику
        result = await handler(event, data)
        return result

    @staticmethod
    async def _update_username(
        user: Employee,
        event: Union[Message, CallbackQuery, InlineQuery],
        stp_repo: MainRequestsRepo,
    ):
        """Обновление юзернейма пользователя если он отличается от сохраненного.

        Args:
            user: Экземпляр пользователя с моделью Employee
            event: Событие
            stp_repo: Репозиторий операций с базой STP
        """
        if not user:
            return

        current_username = event.from_user.username
        stored_username = user.username

        if stored_username != current_username:
            try:
                if current_username is None:
                    await stp_repo.employee.update_user(
                        user_id=event.from_user.id,
                        username=None,
                    )
                    logger.info(
                        f"[Юзернейм] Удален юзернейм пользователя {event.from_user.id}"
                    )
                else:
                    await stp_repo.employee.update_user(
                        user_id=event.from_user.id, username=current_username
                    )
                    logger.info(
                        f"[Юзернейм] Обновлен юзернейм пользователя {event.from_user.id} - @{current_username}"
                    )
            except Exception as e:
                logger.error(
                    f"[Юзернейм] Ошибка обновления юзернейма для пользователя {event.from_user.id}: {e}"
                )

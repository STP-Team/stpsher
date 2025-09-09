import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, InlineQuery, Message

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.services.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class UsersMiddleware(BaseMiddleware):
    """
    Middleware responsible for user access control and banning logic.
    Checks if user exists in database and has sufficient permissions.
    """

    async def __call__(
        self,
        handler: Callable[
            [Union[Message, CallbackQuery, InlineQuery], Dict[str, Any]], Awaitable[Any]
        ],
        event: Union[Message, CallbackQuery, InlineQuery],
        data: Dict[str, Any],
    ) -> Any:
        # Get user and repos from previous middleware (DatabaseMiddleware)
        user: Employee = data.get("user")
        stp_repo: MainRequestsRepo = data.get("stp_repo")

        if user:
            await self._update_username(user, event, stp_repo)

        # Continue to the next middleware/handler
        result = await handler(event, data)
        return result

    @staticmethod
    async def _update_username(
        user: Employee,
        event: Union[Message, CallbackQuery, InlineQuery],
        stp_repo: MainRequestsRepo,
    ):
        """
        Обновление юзернейма пользователя если он отличается от записанного
        :param user:
        :param event:
        :return:
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

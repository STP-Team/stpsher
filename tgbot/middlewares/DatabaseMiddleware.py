import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message
from sqlalchemy.exc import DBAPIError, DisconnectionError, OperationalError

from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import Config
from tgbot.services.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """
    Middleware responsible only for database connections and session management.
    Provides database repositories to other middlewares and handlers.
    """

    def __init__(
        self, config: Config, bot: Bot, stp_session_pool, achievements_session_pool
    ) -> None:
        self.stp_session_pool = stp_session_pool
        self.achievements_session_pool = achievements_session_pool
        self.bot = bot
        self.config = config

    async def __call__(
        self,
        handler: Callable[
            [Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]
        ],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Use separate sessions for different databases
                async with self.stp_session_pool() as stp_session:
                    async with self.achievements_session_pool() as achievements_session:
                        # Create repositories for different databases
                        stp_repo = RequestsRepo(stp_session)  # Для основной базы СТП
                        achievements_repo = RequestsRepo(
                            achievements_session
                        )  # Для базы достижений

                        # Получаем пользователя из БД
                        user = await stp_repo.users.get_user(user_id=event.from_user.id)

                        # Add repositories and user to data for other middlewares
                        data["stp_repo"] = stp_repo
                        data["stp_session"] = stp_session
                        data["achievements_session"] = achievements_session
                        data["achievements_repo"] = achievements_repo
                        data["user"] = user

                        # Continue to the next middleware/handler
                        result = await handler(event, data)
                        return result

            except (OperationalError, DBAPIError, DisconnectionError) as e:
                if "Connection is busy" in str(e) or "HY000" in str(e):
                    retry_count += 1
                    logger.warning(
                        f"[DatabaseMiddleware] Database connection error, retry {retry_count}/{max_retries}: {e}"
                    )
                    if retry_count >= max_retries:
                        logger.error(
                            f"[DatabaseMiddleware] All database connection attempts exhausted: {e}"
                        )
                        if isinstance(event, Message):
                            try:
                                await event.reply(
                                    "⚠️ Временные проблемы с базой данных. Попробуйте позже."
                                )
                            except:
                                pass
                        return None
                else:
                    logger.error(f"[DatabaseMiddleware] Critical database error: {e}")
                    return None
            except Exception as e:
                logger.error(f"[DatabaseMiddleware] Unexpected error: {e}")
                return None

        return None

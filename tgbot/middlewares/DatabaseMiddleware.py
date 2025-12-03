"""Middleware для доступа к базам данных."""

import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message
from sqlalchemy.exc import DBAPIError, DisconnectionError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from stp_database.repo.KPI.requests import KPIRequestsRepo
from stp_database.repo.STP import MainRequestsRepo

from tgbot.config import Config

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """Middleware, отвечающий за подключение к базе данных и управление сессиями.

    Предоставляет репозитории баз данных другим middleware и обработчикам
    """

    def __init__(
        self,
        config: Config,
        bot: Bot,
        stp_session_pool: async_sessionmaker[AsyncSession],
        kpi_session_pool: async_sessionmaker[AsyncSession],
    ) -> None:
        """Инициализация миддлвари для связи с БД."""
        self.stp_session_pool = stp_session_pool
        self.kpi_session_pool = kpi_session_pool
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
        """Обработка запросов к миддлвари.

        Args:
            handler: Обработчик сообщений и CallbackQuery от Telegram
            event: Событие Telegram
            data: Данные в памяти

        Returns:
            Заполненные stp_repo, stp_session, kpi_repo, kpi_session, user
        """
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Используем раздельные сессии для баз данных
                async with self.stp_session_pool() as stp_session:
                    stp_repo = MainRequestsRepo(stp_session)
                    data["stp_repo"] = stp_repo
                    data["stp_session"] = stp_session
                    data["user"] = await stp_repo.employee.get_users(
                        user_id=event.from_user.id
                    )
                    # Добавляем пулы сессий для доступа в error handlers
                    data["stp_session_pool"] = self.stp_session_pool
                    data["kpi_session_pool"] = self.kpi_session_pool

                    async with self.kpi_session_pool() as kpi_session:
                        kpi_repo = KPIRequestsRepo(kpi_session)
                        data["kpi_repo"] = kpi_repo
                        data["kpi_session"] = kpi_session

                        # Продолжаем к следующему middleware/обработчику
                        result = await handler(event, data)
                        return result

            except (OperationalError, DBAPIError, DisconnectionError) as e:
                if "Connection is busy" in str(e) or "HY000" in str(e):
                    retry_count += 1
                    logger.warning(
                        f"[DatabaseMiddleware] Ошибка подключения к базе данных, повтор {retry_count}/{max_retries}: {e}"
                    )
                    if retry_count >= max_retries:
                        logger.error(
                            f"[DatabaseMiddleware] Потрачены все попытки подключения к базе данных: {e}"
                        )
                        if isinstance(event, Message):
                            try:
                                await event.reply(
                                    "⚠️ Временные проблемы с базой данных. Попробуй позже."
                                )
                            except Exception as e:
                                logger.error(
                                    f"[База данных] Произошла ошибка при доступе к базе данных: {e}"
                                )
                                pass
                        return None
                else:
                    logger.error(
                        f"[DatabaseMiddleware] Критическая ошибка базы данных: {e}"
                    )
                    return None
            except Exception as e:
                logger.error(f"[DatabaseMiddleware] Неожиданная ошибка: {e}")
                return None

        return None

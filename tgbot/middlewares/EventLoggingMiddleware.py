"""Middleware для логирования событий пользователей."""

import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message
from stp_database import Employee, MainRequestsRepo

from tgbot.services.event_logger import EventLogger

logger = logging.getLogger(__name__)


class EventLoggingMiddleware(BaseMiddleware):
    """Middleware для автоматического логирования событий взаимодействия пользователей."""

    async def __call__(
        self,
        handler: Callable[
            [Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]
        ],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        """Обрабатывает события и логирует их в базу данных.

        Args:
            handler: Следующий обработчик в цепочке
            event: Событие (Message или CallbackQuery)
            data: Данные middleware (содержит stp_repo, user и т.д.)

        Returns:
            Результат выполнения обработчика
        """
        # Получаем данные из предыдущих middleware
        stp_repo: MainRequestsRepo = data.get("stp_repo")
        user: Employee = data.get("user")

        # Проверяем наличие необходимых данных
        if not stp_repo or not user:
            # Если нет репозитория или пользователя, просто продолжаем
            return await handler(event, data)

        # Создаем EventLogger и добавляем его в data для использования в handlers
        event_logger = EventLogger(stp_repo)
        data["event_logger"] = event_logger

        # Получаем DialogManager для доступа к session_id
        aiogd_context = data.get("aiogd_context")

        try:
            session_id = aiogd_context.id
            prev_state = aiogd_context.state.state
        except (AttributeError, TypeError):
            # Если aiogd_context отсутствует или не имеет нужных атрибутов, пропускаем логирование
            logger.debug(
                f"[EventLoggingMiddleware] aiogd_context недоступен для пользователя {user.user_id}"
            )
            return await handler(event, data)

        try:
            # Логируем событие в зависимости от типа
            if isinstance(event, Message):
                # Логируем сообщение
                event_type = "message"
                if event.text and event.text.startswith("/"):
                    event_type = "command"

                await event_logger.log_event(
                    user_id=user.user_id,
                    event_type=event_type,
                    event_category="interaction",
                    session_id=session_id,
                    text=event.text if event.text else None,
                    dialog_state=f"{prev_state}",
                    content_type=event.content_type,
                )

            elif isinstance(event, CallbackQuery):
                new_state = event.data.split("\x1d")[1]

                # Логируем callback query
                await event_logger.log_event(
                    user_id=user.user_id,
                    event_type="callback_query",
                    event_category="interaction",
                    session_id=session_id,
                    dialog_state=f"{prev_state}",
                    window_name=new_state,
                    callback_data=event.data,
                    widget_data=aiogd_context.widget_data,
                )

        except Exception as e:
            # Не прерываем обработку если логирование не удалось
            logger.error(f"[EventLoggingMiddleware] Ошибка логирования события: {e}")

        # Продолжаем выполнение обработчика
        return await handler(event, data)

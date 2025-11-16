"""Логирование событий."""

from stp_database import MainRequestsRepo


class EventLogger:
    """Класс логера событий."""

    def __init__(self, stp_repo: MainRequestsRepo):
        """Инициализация логера."""
        self.repo = stp_repo

    async def log_event(
        self,
        user_id: int,
        event_type: str,
        event_category: str,
        session_id: str = None,
        window_name: str = None,
        dialog_state: str = None,
        **metadata,
    ) -> None:
        """Логирование события в БД.

        Args:
            user_id: ID пользователя
            event_type: Тип события
            event_category: Категория события
            session_id: ID сессии
            window_name: Название окна
            dialog_state: Состояние диалога
            **metadata: Дополнительная метадата
        """
        await self.repo.event_log.create_event(
            user_id=user_id,
            event_type=event_type,
            event_category=event_category,
            session_id=session_id,
            window_name=window_name,
            dialog_state=dialog_state,
            metadata=metadata,
        )

    async def log_bot_start(self, user_id: int) -> None:
        """Логирование запуска бота.

        Args:
            user_id: ID пользователя
        """
        await self.log_event(user_id, "bot_start", "system")

    async def log_window_open(
        self,
        user_id: int,
        window_name: str,
        session_id: str = None,
        dialog_state: str = None,
    ) -> None:
        """Логирование открытия окна.

        Args:
            user_id: ID пользователя
            window_name: Название окна
            session_id: ID сессии
            dialog_state: Состояние диалога
        """
        await self.log_event(
            user_id,
            "window_open",
            "navigation",
            session_id=session_id,
            window_name=window_name,
            dialog_state=dialog_state,
        )

    async def log_casino_play(self, user_id: int, game_type: str, result: dict) -> None:
        """Логирование игры в казино.

        Args:
            user_id: ID пользователя
            game_type: Тип игры
            result: Результат игры
        """
        await self.log_event(
            user_id, "casino_play", "game", game_type=game_type, **result
        )

    async def log_achievement(self, user_id: int, achievement_id: int) -> None:
        """Логирование получения достижения.

        Args:
            user_id: ID пользователя
            achievement_id: ID достижения
        """
        await self.log_event(
            user_id, "achievement_unlock", "achievement", achievement_id=achievement_id
        )

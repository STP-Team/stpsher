from stp_database import MainRequestsRepo


class EventLogger:
    def __init__(self, stp_repo: MainRequestsRepo):
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
    ):
        """Log an event to database"""
        await self.repo.event_log.create_event(
            user_id=user_id,
            event_type=event_type,
            event_category=event_category,
            session_id=session_id,
            window_name=window_name,
            dialog_state=dialog_state,
            metadata=metadata,
        )

    # Convenient methods
    async def log_bot_start(self, user_id: int):
        await self.log_event(user_id, "bot_start", "system")

    async def log_window_open(
        self,
        user_id: int,
        window_name: str,
        session_id: str = None,
        dialog_state: str = None,
    ):
        await self.log_event(
            user_id,
            "window_open",
            "navigation",
            session_id=session_id,
            window_name=window_name,
            dialog_state=dialog_state,
        )

    async def log_casino_play(self, user_id: int, game_type: str, result: dict):
        await self.log_event(
            user_id, "casino_play", "game", game_type=game_type, **result
        )

    async def log_achievement(self, user_id: int, achievement_id: int):
        await self.log_event(
            user_id, "achievement_unlock", "achievement", achievement_id=achievement_id
        )

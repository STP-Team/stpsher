"""Base scheduler class."""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)


class BaseScheduler(ABC):
    """Base scheduler class providing common interface."""

    def __init__(self, category_name: str):
        self.category_name = category_name
        self.logger = logging.getLogger(f"{__name__}.{category_name}")

    @abstractmethod
    def setup_jobs(self, scheduler: AsyncIOScheduler, stp_session_pool, bot: Bot):
        """Setup scheduler jobs."""
        pass

    def _add_job(
        self,
        scheduler: AsyncIOScheduler,
        func,
        trigger,
        job_id: str,
        name: Optional[str] = None,
        **trigger_args,
    ) -> None:
        """Add job to scheduler."""
        try:
            scheduler.add_job(
                func=func,
                trigger=trigger,
                id=f"{self.category_name}_{job_id}",
                name=name or f"{self.category_name} - {job_id}",
                **trigger_args,
            )
            self.logger.info(f"Task '{name or job_id}' configured")
        except Exception as e:
            self.logger.error(f"Task '{name or job_id}' error: {e}")
            raise

    def _log_job_execution(
        self, job_name: str, success: bool = True, error: str = None
    ) -> None:
        """Log job execution result."""
        if success:
            self.logger.info(f"Task completed: {job_name}")
        else:
            self.logger.error(f"Task failed {job_name}: {error}")

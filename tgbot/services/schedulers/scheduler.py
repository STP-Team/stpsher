"""Scheduler service manager."""

import logging

from aiogram import Bot
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tgbot.config import load_config
from tgbot.misc.helpers import tz_perm
from tgbot.services.schedulers.achievements import AchievementScheduler
from tgbot.services.schedulers.exchanges import ExchangesScheduler
from tgbot.services.schedulers.hr import HRScheduler
from tgbot.services.schedulers.studies import StudiesScheduler
from tgbot.services.schedulers.tutors import TutorsScheduler

config = load_config(".env")
logger = logging.getLogger(__name__)


class SchedulerManager:
    """Scheduler manager."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._configure()
        self.hr = HRScheduler()
        self.achievements = AchievementScheduler()
        self.studies = StudiesScheduler()
        self.exchanges = ExchangesScheduler()
        self.tutors = TutorsScheduler()

    def _configure(self):
        jobstores = {"default": MemoryJobStore()}
        if config.tg_bot.use_redis:
            jobstores["redis"] = RedisJobStore(
                host=config.redis.redis_host,
                port=config.redis.redis_port,
                password=config.redis.redis_pass,
                db=1,
            )

        self.scheduler.configure(
            jobstores=jobstores,
            job_defaults={
                "coalesce": True,
                "misfire_grace_time": 300,
                "replace_existing": True,
            },
            timezone=tz_perm,
        )

    def setup_jobs(
        self,
        stp_session_pool: async_sessionmaker[AsyncSession],
        stats_session_pool: async_sessionmaker[AsyncSession],
        bot: Bot,
    ) -> None:
        """Setup all scheduled tasks."""
        logger.info("[Scheduler] Setting up tasks...")

        self.hr.setup_jobs(self.scheduler, stp_session_pool, bot)
        self.achievements.setup_jobs(
            self.scheduler, stp_session_pool, stats_session_pool, bot
        )
        self.studies.setup_jobs(self.scheduler, stp_session_pool, bot)
        self.exchanges.setup_jobs(self.scheduler, stp_session_pool, bot)
        self.tutors.setup_jobs(
            self.scheduler, stp_session_pool, stats_session_pool, bot
        )

        logger.info("[Scheduler] All tasks configured")

    def start(self):
        """Start scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("[Scheduler] Started")

    def shutdown(self):
        """Stop scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("[Scheduler] Stopped")

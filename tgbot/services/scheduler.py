import logging
from typing import Dict

import pytz
from aiogram import Bot
from apscheduler.jobstores.base import BaseJobStore
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from tgbot.config import load_config
from tgbot.services.schedulers.achievements import AchievementScheduler
from tgbot.services.schedulers.hr import HRScheduler

config = load_config(".env")
logger = logging.getLogger(__name__)


class SchedulerManager:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._configure_scheduler()

        # Initialize category schedulers
        self.hr = HRScheduler()
        self.achievements = AchievementScheduler()

    def _configure_scheduler(self):
        job_defaults = {
            "coalesce": True,
            "misfire_grace_time": 300,
            "replace_existing": True,
        }

        jobstores: Dict[str, BaseJobStore] = {"default": MemoryJobStore()}

        if config.tg_bot.use_redis:
            REDIS = {
                "host": config.redis.redis_host,
                "port": config.redis.redis_port,
                "password": config.redis.redis_pass,
                "db": 1,
                "ssl": False,
                "decode_responses": False,
            }
            jobstores["redis"] = RedisJobStore(**REDIS)

        self.scheduler.configure(
            jobstores=jobstores,
            job_defaults=job_defaults,
            timezone=pytz.timezone("Asia/Yekaterinburg"),
        )

    def setup_jobs(self, session_pool, bot: Bot, kpi_session_pool=None):
        """
        Настройка всех запланированных задач

        Args:
            session_pool: Пул сессий основной БД
            bot: Экземпляр бота
            kpi_session_pool: Пул сессий KPI БД (опционально)
        """
        logger.info("[Scheduler] Настройка запланированных задач...")

        # HR задачи
        self.hr.setup_jobs(self.scheduler, session_pool, bot)

        # Задачи достижений
        self.achievements.setup_jobs(
            self.scheduler, session_pool, bot, kpi_session_pool
        )

        logger.info("[Scheduler] Все задачи настроены")

    def start(self):
        """Запуск планировщика"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("[Scheduler] Планировщик запущен")

    def shutdown(self):
        """Остановка планировщика"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("[Scheduler] Планировщик остановлен")

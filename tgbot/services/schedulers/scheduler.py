"""Сервис отложенных задач."""

import logging
from typing import Dict

from aiogram import Bot
from apscheduler.jobstores.base import BaseJobStore
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from tgbot.config import IS_DEVELOPMENT, load_config
from tgbot.misc.helpers import tz
from tgbot.services.schedulers.achievements import AchievementScheduler
from tgbot.services.schedulers.exchanges import ExchangesScheduler
from tgbot.services.schedulers.hr import HRScheduler
from tgbot.services.schedulers.studies import StudiesScheduler

config = load_config(".env")
logger = logging.getLogger(__name__)


class SchedulerManager:
    """Менеджер планировщика."""

    def __init__(self):
        """Инициализация менеджера планировщика.

        Создает экземпляр AsyncIOScheduler, настраивает его параметры
        и инициализирует все специализированные планировщики (HR, достижения, обучения).

        Attributes:
            self.scheduler: Асинхронный планировщик задач APScheduler
            self.hr: Планировщик задач по HR
            self.achievements: Планировщик задач по достижениям
            self.studies: Планировщик задач по обучениям
        """
        self.scheduler = AsyncIOScheduler()
        self._configure_scheduler()

        # Инициализация планировщиков
        self.hr = HRScheduler()
        self.achievements = AchievementScheduler()
        self.studies = StudiesScheduler()
        self.exchanges = ExchangesScheduler()

    def _configure_scheduler(self):
        job_defaults = {
            "coalesce": True,
            "misfire_grace_time": 300,
            "replace_existing": True,
        }

        jobstores: Dict[str, BaseJobStore] = {"default": MemoryJobStore()}

        if config.tg_bot.use_redis:
            redis = {
                "host": config.redis.redis_host,
                "port": config.redis.redis_port,
                "password": config.redis.redis_pass,
                "db": 1,
                "ssl": False,
                "decode_responses": False,
            }
            jobstores["redis"] = RedisJobStore(**redis)

        self.scheduler.configure(
            jobstores=jobstores,
            job_defaults=job_defaults,
            timezone=tz,
        )

    def setup_jobs(self, session_pool, bot: Bot, kpi_session_pool) -> None:
        """Настройка всех запланированных задач.

        Args:
            session_pool: Пул сессий основной БД
            bot: Экземпляр бота
            kpi_session_pool: Пул сессий KPI БД
        """
        logger.info("[Планировщик] Настройка запланированных задач...")

        # HR задачи
        self.hr.setup_jobs(self.scheduler, session_pool, bot)

        if not IS_DEVELOPMENT:
            # Задачи достижений
            self.achievements.setup_jobs(
                self.scheduler, session_pool, bot, kpi_session_pool
            )

        # Задачи обучений
        self.studies.setup_jobs(self.scheduler, session_pool, bot)

        # Задачи биржи
        self.exchanges.setup_jobs(self.scheduler, session_pool, bot)

        logger.info("[Планировщик] Все задачи настроены")

    def start(self):
        """Запуск планировщика."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("[Планировщик] Планировщик запущен")

    def shutdown(self):
        """Остановка планировщика."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("[Планировщик] Планировщик остановлен")

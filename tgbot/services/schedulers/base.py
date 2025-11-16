"""Базовый класс для планировщиков задач."""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)


class BaseScheduler(ABC):
    """Базовый класс для всех планировщиков задач.

    Предоставляет общий интерфейс для настройки и управления
    категорией запланированных задач.
    """

    def __init__(self, category_name: str):
        """Инициализация базового класса планировщика."""
        self.category_name = category_name
        self.logger = logging.getLogger(f"{__name__}.{category_name}")

    @abstractmethod
    def setup_jobs(self, scheduler: AsyncIOScheduler, stp_session_pool, bot: Bot):
        """Настройка всех задач данной категории.

        Args:
            scheduler: Экземпляр AsyncIOScheduler
            stp_session_pool: Пул сессий с базой STP
            bot: Экземпляр бота
        """
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
        """Добавляет задачу в планировщик.

        Args:
            scheduler: Планировщик
            func: Функция для выполнения
            trigger: Тип триггера ('cron', 'interval', etc.)
            job_id: Уникальный ID задачи
            name: Читаемое имя задачи
            **trigger_args: Аргументы для триггера
        """
        try:
            scheduler.add_job(
                func=func,
                trigger=trigger,
                id=f"{self.category_name}_{job_id}",
                name=name or f"{self.category_name} - {job_id}",
                **trigger_args,
            )
            self.logger.info(
                f"[{self.category_name}] Задача '{name or job_id}' настроена успешно"
            )
        except Exception as e:
            self.logger.error(
                f"[{self.category_name}] Ошибка настройки задачи '{name or job_id}': {e}"
            )
            raise

    def _log_job_execution_start(self, job_name: str) -> None:
        """Логирование начала выполнения задачи.

        Args:
            job_name: Название задачи.
        """
        self.logger.info(f"[{self.category_name}] Начало выполнения задачи: {job_name}")

    def _log_job_execution_end(
        self, job_name: str, success: bool = True, error: str = None
    ) -> None:
        """Логирование завершения выполнения задачи.

        Args:
            job_name: Нзавание задачи
            success: Успешно или нет
            error: Текст ошибки
        """
        if success:
            self.logger.info(
                f"[{self.category_name}] Задача завершена успешно: {job_name}"
            )
        else:
            self.logger.error(
                f"[{self.category_name}] Ошибка выполнения задачи {job_name}: {error}"
            )

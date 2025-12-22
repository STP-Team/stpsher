"""Планировщик уведомлений о занятиях наставничества."""

import logging
from datetime import datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import async_sessionmaker
from stp_database.repo.Stats.requests import StatsRequestsRepo
from stp_database.repo.STP import MainRequestsRepo

from tgbot.misc.helpers import format_fullname, tz_perm
from tgbot.services.broadcaster import send_message

from .base import BaseScheduler

logger = logging.getLogger(__name__)


class TutorsScheduler(BaseScheduler):
    """Планировщик уведомлений о предстоящих занятиях наставничества.

    Отправляет уведомления наставникам и стажерам за час до начала занятия.
    """

    def __init__(self):
        """Инициализация планировщика наставничества."""
        super().__init__("tutors")

    def setup_jobs(
        self,
        scheduler: AsyncIOScheduler,
        stp_session_pool: async_sessionmaker,
        stats_session_pool: async_sessionmaker,
        bot: Bot,
    ):
        """Настройка задач планировщика наставничества.

        Args:
            scheduler: Экземпляр AsyncIOScheduler
            stp_session_pool: Пул сессий с базой STP
            stats_session_pool: Пул сессий с базой Stats
            bot: Экземпляр бота
        """
        # Проверка предстоящих занятий каждую минуту
        self._add_job(
            scheduler=scheduler,
            func=self._check_upcoming_training_job,
            trigger="interval",
            job_id="check_upcoming_training",
            name="Проверка предстоящих занятий наставничества",
            minutes=1,
            args=[stp_session_pool, stats_session_pool, bot],
        )

    async def _check_upcoming_training_job(
        self,
        stp_session_pool: async_sessionmaker,
        stats_session_pool: async_sessionmaker,
        bot: Bot,
    ):
        """Обертка для проверки предстоящих занятий с логированием."""
        self._log_job_execution_start("Проверка предстоящих занятий")
        try:
            await self._check_upcoming_training(
                stp_session_pool, stats_session_pool, bot
            )
            self._log_job_execution_end("Проверка предстоящих занятий", success=True)
        except Exception as e:
            self._log_job_execution_end(
                "Проверка предстоящих занятий", success=False, error=str(e)
            )

    async def _check_upcoming_training(
        self,
        stp_session_pool: async_sessionmaker,
        stats_session_pool: async_sessionmaker,
        bot: Bot,
    ):
        """Проверяет предстоящие занятия и отправляет уведомления за час до начала.

        Args:
            stp_session_pool: Пул сессий с базой STP
            stats_session_pool: Пул сессий с базой Stats
            bot: Экземпляр бота
        """
        now = datetime.now(tz_perm)
        current_date = now.date()
        notification_time = now + timedelta(hours=1)

        # Окно для поиска занятий (±2 минуты от целевого времени уведомления)
        time_window_start = notification_time - timedelta(minutes=2)
        time_window_end = notification_time + timedelta(minutes=2)

        # Получаем занятия на текущий день
        async with stats_session_pool() as stats_session:
            async with stats_session.begin():
                stats_repo = StatsRequestsRepo(stats_session)

                # Получаем все занятия на сегодня
                trainings = await stats_repo.tutors_schedule.get_tutor_trainees_by_date(
                    training_date=current_date
                )

        if not trainings:
            return

        # Ищем занятия, которые начинаются в интервале уведомления
        upcoming_trainings = []
        for training in trainings:
            if not training.training_start_time:
                continue

            # Применяем timezone к naive datetime
            training_start_aware = tz_perm.localize(training.training_start_time)

            if time_window_start <= training_start_aware <= time_window_end:
                upcoming_trainings.append(training)

        if not upcoming_trainings:
            return

        self.logger.info(f"Найдено {len(upcoming_trainings)} предстоящих занятий")

        # Отправляем уведомления
        async with stp_session_pool() as main_session:
            async with main_session.begin():
                main_repo = MainRequestsRepo(main_session)

                for training in upcoming_trainings:
                    await self._send_training_notifications(main_repo, bot, training)

    async def _send_training_notifications(
        self, main_repo: MainRequestsRepo, bot: Bot, training
    ):
        """Отправляет уведомления наставнику и стажеру о предстоящем занятии.

        Args:
            main_repo: Репозиторий для работы с основной базой
            bot: Экземпляр бота
            training: Объект с данными о занятии
        """
        training_start_time = training.training_start_time.strftime("%H:%M")
        training_end_time = training.training_end_time.strftime("%H:%M")

        # Получаем user_id наставника
        tutor_user = None
        if training.tutor_fullname:
            tutor_user = await main_repo.employee.get_users(
                fullname=training.tutor_fullname
            )

        # Получаем user_id стажера
        trainee_user = None
        if training.trainee_fullname:
            trainee_user = await main_repo.employee.get_users(
                fullname=training.trainee_fullname
            )

        # Уведомление наставнику
        if tutor_user and tutor_user.user_id:
            tutor_message = (
                f"🎓 Наставничество\n\n"
                f"<b>Время стажировки:</b> {training_start_time}-{training_end_time}\n"
                f"<b>Стажер:</b> {format_fullname(trainee_user, True, True) or 'Не указан'}\n\n"
                f"Занятие начнется через час"
            )

            success = await send_message(bot, tutor_user.user_id, tutor_message)
            if success:
                self.logger.info(
                    f"Уведомление отправлено наставнику {training.tutor_fullname}"
                )
            else:
                self.logger.warning(
                    f"Не удалось отправить уведомление наставнику {tutor_user.user_id}"
                )

        # Уведомление стажеру
        if trainee_user and trainee_user.user_id:
            trainee_message = (
                f"📚 Стажировка\n\n"
                f"<b>Время стажировки:</b> {training_start_time}-{training_end_time}\n"
                f"<b>Наставник:</b> {format_fullname(tutor_user, True, True) or 'Не указан'}\n\n"
                f"Занятие начнется через час"
            )

            success = await send_message(bot, trainee_user.user_id, trainee_message)
            if success:
                self.logger.info(
                    f"Уведомление отправлено стажеру {training.trainee_fullname}"
                )
            else:
                self.logger.warning(
                    f"Не удалось отправить уведомление стажеру {trainee_user.user_id}"
                )

        # Логируем успешную отправку уведомления о занятии
        self.logger.info(
            f"Обработано занятие: {training.tutor_fullname} -> {training.trainee_fullname} "
            f"в {training_start_time}"
        )

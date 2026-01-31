"""Tutors notification scheduler."""

import logging
from datetime import datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import async_sessionmaker
from stp_database.repo.Stats.requests import StatsRequestsRepo
from stp_database.repo.STP import MainRequestsRepo

from tgbot.misc.helpers import format_fullname, tz_perm
from tgbot.services.broadcaster import send_message
from tgbot.services.schedulers.base import BaseScheduler

logger = logging.getLogger(__name__)
TIME_WINDOW = timedelta(minutes=2)
NOTIFY_BEFORE = timedelta(hours=1)


class TutorsScheduler(BaseScheduler):
    """Tutoring session notification scheduler."""

    def __init__(self):
        super().__init__("tutors")
        self._sent = set()
        self._last_reset = None

    def setup_jobs(self, scheduler: AsyncIOScheduler, stp_session_pool: async_sessionmaker,
                   stats_session_pool: async_sessionmaker, bot: Bot):
        self._add_job(
            scheduler=scheduler,
            func=self._check_job,
            trigger="interval",
            job_id="check_upcoming",
            name="Проверка предстоящих занятий",
            minutes=1,
            args=[stp_session_pool, stats_session_pool, bot],
        )

    async def _check_job(self, stp_session_pool, stats_session_pool, bot):
        self._log_job_execution("Проверка занятий", True)
        try:
            await self._check_training(stp_session_pool, stats_session_pool, bot)
            self._log_job_execution("Проверка занятий", True)
        except Exception as e:
            self._log_job_execution("Проверка занятий", False, str(e))

    def _reset_if_needed(self, today):
        if self._last_reset != today:
            self._sent.clear()
            self._last_reset = today
            logger.info("Reset notification tracking")

    def _key(self, training):
        return f"{training.tutor_fullname}|{training.trainee_fullname}|{training.training_start_time.strftime('%H:%M')}"

    async def _check_training(self, stp_session_pool, stats_session_pool, bot):
        now = datetime.now(tz_perm)
        self._reset_if_needed(now.date())

        target = now + NOTIFY_BEFORE
        start, end = target - TIME_WINDOW, target + TIME_WINDOW

        async with stats_session_pool() as stats_session:
            repo = StatsRequestsRepo(stats_session)
            trainings = await repo.tutors_schedule.get_tutor_trainees_by_date(training_date=now.date())

        upcoming = [
            t for t in trainings
            if t.training_start_time
            and start <= tz_perm.localize(t.training_start_time) <= end
            and self._key(t) not in self._sent
        ]

        if not upcoming:
            return

        logger.info(f"Found {len(upcoming)} upcoming sessions")

        async with stp_session_pool() as main_session:
            repo = MainRequestsRepo(main_session)
            for t in upcoming:
                await self._notify(repo, bot, t)
                self._sent.add(self._key(t))

    async def _notify(self, repo: MainRequestsRepo, bot: Bot, training):
        times = f"{training.training_start_time.strftime('%H:%M')}-{training.training_end_time.strftime('%H:%M')} ПРМ"

        tutor = await repo.employee.get_users(fullname=training.tutor_fullname) if training.tutor_fullname else None
        trainee = await repo.employee.get_users(fullname=training.trainee_fullname) if training.trainee_fullname else None

        if tutor and tutor.user_id:
            msg = f"🎓 <b>Наставничество</b>\n\n<b>Время:</b> {times}\n<b>Стажер:</b> {format_fullname(trainee, True, True) or 'Не указан'}\n\nЗанятие начнется через час"
            await send_message(bot, tutor.user_id, msg)

        if trainee and trainee.user_id:
            msg = f"📚 <b>Стажировка</b>\n\n<b>Время:</b> {times}\n<b>Наставник:</b> {format_fullname(tutor, True, True) or 'Не указан'}\n\nЗанятие начнется через час"
            await send_message(bot, trainee.user_id, msg)

        logger.info(f"Notified: {training.tutor_fullname} -> {training.trainee_fullname}")

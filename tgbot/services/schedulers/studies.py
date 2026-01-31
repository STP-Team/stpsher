"""Studies notification scheduler."""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Set

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from stp_database.repo.STP import MainRequestsRepo

from tgbot.misc.helpers import format_fullname
from tgbot.services.broadcaster import send_message
from tgbot.services.files_processing.parsers.studies import StudiesScheduleParser
from tgbot.services.schedulers.base import BaseScheduler

logger = logging.getLogger(__name__)
STUDIES_FILE = Path("uploads/Обучения.xlsx")
CHECK_WINDOW = timedelta(minutes=10)


class StudiesScheduler(BaseScheduler):
    """Studies notification scheduler."""

    def __init__(self):
        super().__init__("Обучения")

    def setup_jobs(self, scheduler: AsyncIOScheduler, stp_session_pool: async_sessionmaker[AsyncSession], bot: Bot):
        scheduler.add_job(
            func=self._check_job,
            args=[stp_session_pool, bot],
            trigger="interval",
            id=f"{self.category_name}_check",
            name="Проверка предстоящих обучений",
            minutes=30,
        )

    async def _check_job(self, stp_session_pool: async_sessionmaker[AsyncSession], bot: Bot):
        self._log_job_execution("Проверка обучений", True)
        try:
            await check_upcoming_studies(stp_session_pool, bot)
            self._log_job_execution("Проверка обучений", True)
        except Exception as e:
            self._log_job_execution("Проверка обучений", False, str(e))


async def check_upcoming_studies(stp_session_pool: async_sessionmaker[AsyncSession], bot: Bot):
    """Check upcoming studies and send notifications."""
    if not STUDIES_FILE.exists():
        logger.warning("[Studies] File not found")
        return {"status": "error", "message": "File not found"}

    parser = StudiesScheduleParser()
    all_sessions = parser.parse_studies_file(STUDIES_FILE)
    if not all_sessions:
        return {"status": "success", "message": "No sessions"}

    now = datetime.now()
    upcoming = [
        s for s in all_sessions
        if abs((s.date - now) - timedelta(hours=2)) <= CHECK_WINDOW
        or abs((s.date - now) - timedelta(hours=1)) <= CHECK_WINDOW
    ]

    if not upcoming:
        return {"status": "success", "message": "No upcoming sessions"}

    results = await send_study_notifications(upcoming, stp_session_pool, bot)
    total = sum(results.values())
    logger.info(f"[Studies] Sent {total} notifications for {len(upcoming)} sessions")

    return {"status": "success", "sessions": len(upcoming), "notifications": total, "results": results}


async def send_study_notifications(sessions, stp_session_pool: async_sessionmaker[AsyncSession], bot: Bot) -> dict:
    """Send notifications to study participants."""
    results = {}

    async with stp_session_pool() as session:
        repo = MainRequestsRepo(session)

        for session_obj in sessions:
            key = f"{session_obj.date.strftime('%d.%m.%Y')}_{session_obj.title}"
            sent = 0

            participants: Set[str] = {
                name.strip() for _, name, _, _, _ in session_obj.participants if name and name.strip()
            }

            for name in participants:
                try:
                    user = await repo.employee.get_users(fullname=name)
                    if not user or not user.user_id:
                        continue

                    msg = await _create_notification_message(session_obj, repo, user)
                    if await send_message(bot, user.user_id, msg):
                        sent += 1
                except Exception as e:
                    logger.error(f"[Studies] Error notifying {name}: {e}")

            results[key] = sent
            logger.info(f"[Studies] {key}: {sent} notifications sent")

    return results


async def _create_notification_message(session, repo, user) -> str:
    """Create study notification message."""
    time_diff = session.date - datetime.now()

    if abs(time_diff - timedelta(hours=2)) <= timedelta(minutes=10):
        time_text = "через 2 часа"
    elif abs(time_diff - timedelta(hours=1)) <= timedelta(minutes=10):
        time_text = "через 1 час"
    else:
        days = (session.date.date() - datetime.now().date()).days
        time_text = "сегодня" if days == 0 else "завтра" if days == 1 else f"через {days} дн."

    trainer = session.trainer
    if trainer:
        try:
            trainer_user = await repo.employee.get_users(fullname=trainer)
            trainer = format_fullname(trainer_user) if trainer_user else trainer
        except Exception:
            pass

    return (
        f"📚 <b>Напоминание об обучении</b>\n"
        f"Напоминаем, что <b>{time_text}</b> у тебя запланировано обучение:\n"
        f"📖 <b>Тема:</b> {session.title}\n"
        f"🎓 <b>Тренер:</b> {trainer}\n"
        f"📅 <b>Дата:</b> {session.date.strftime('%d.%m.%Y')} {session.time} "
        f"{'(' + session.duration + ')' if session.duration else ''}\n"
        "\n<blockquote expandable>💡 <b>Правила посещения</b>"
        "• Подтверди или отклони явку в письме на почте"
        "• Крайний срок предупреждения - за 2 часа до начала"
        "• Обязательно наличие камеры</blockquote>"
    )

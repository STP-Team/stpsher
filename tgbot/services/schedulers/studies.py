"""Studies scheduler for managing study session notifications.

Handles notifications for participants when there's less than a week before study dates.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Set

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from stp_database import MainRequestsRepo

from tgbot.services.broadcaster import send_message
from tgbot.services.files_processing.parsers.studies import (
    StudiesScheduleParser,
    StudySession,
)
from tgbot.services.schedulers.base import BaseScheduler

logger = logging.getLogger(__name__)


class StudiesScheduler(BaseScheduler):
    """Studies scheduler for managing study session notifications

    Manages notifications for study participants when there's less than a week
    before the study date.
    """

    def __init__(self):
        super().__init__("Обучения")
        self.studies_parser = StudiesScheduleParser()

    def setup_jobs(self, scheduler: AsyncIOScheduler, session_pool, bot: Bot):
        """Setup all studies-related jobs"""
        self.logger.info("Настройка задач уведомлений об обучениях...")

        # Проверка приближающихся обучений
        scheduler.add_job(
            func=self._check_upcoming_studies_job,
            args=[session_pool, bot],
            trigger="interval",
            id=f"{self.category_name}_check_upcoming_studies",
            name="Проверка предстоящих обучений",
            minutes=30,
        )

    async def _check_upcoming_studies_job(self, session_pool, bot: Bot):
        """Wrapper for checking upcoming studies"""
        self._log_job_execution_start("Проверка предстоящих обучений")
        try:
            result = await check_upcoming_studies(session_pool, bot)
            self._log_job_execution_end("Проверка предстоящих обучений", success=True)
            return result
        except Exception as e:
            self._log_job_execution_end(
                "Проверка предстоящих обучений", success=False, error=str(e)
            )


async def check_upcoming_studies(session_pool, bot: Bot):
    """Check for upcoming studies and notify participants if less than a week away

    Args:
        session_pool: Database session pool
        bot: Bot instance for sending notifications

    Returns:
        Dict with notification results
    """
    try:
        # Get all studies from the file
        studies_parser = StudiesScheduleParser()
        file_path = Path("uploads/Обучения.xlsx")

        if not file_path.exists():
            logger.warning("[Обучения] Файл обучений не найден: Обучения.xlsx")
            return {"status": "error", "message": "Файл обучений не найден"}

        all_sessions = studies_parser.parse_studies_file(file_path)

        if not all_sessions:
            logger.info("[Обучения] No study sessions found in file")
            return {"status": "success", "message": "No study sessions found"}

        # Filter sessions for notifications: 2 hours before OR 1 hour before
        now = datetime.now()

        upcoming_sessions = []
        for session in all_sessions:
            # Calculate time difference
            time_diff = session.date - now

            # Check if it's exactly 2 hours before (within 10 minutes window)
            two_hours_before = timedelta(hours=2)
            if abs(time_diff - two_hours_before) <= timedelta(minutes=10):
                upcoming_sessions.append(session)
                continue

            # Check if it's exactly 1 hour before (within 10 minutes window)
            one_hour_before = timedelta(hours=1)
            if abs(time_diff - one_hour_before) <= timedelta(minutes=10):
                upcoming_sessions.append(session)

        if not upcoming_sessions:
            logger.debug(
                "[Обучения] Нет обучений, требуемых уведомления (за 2 часа или 1 час)"
            )
            return {"status": "success", "message": "No studies requiring notification"}

        logger.info(
            f"[Обучения] Найдено {len(upcoming_sessions)} приближающихся обучений"
        )

        # Send notifications to participants
        notification_results = await send_study_notifications(
            upcoming_sessions, session_pool, bot
        )

        # Log summary
        total_notifications = sum(notification_results.values())
        logger.info(
            f"[Обучения] Отправлено {total_notifications} уведомлений для {len(upcoming_sessions)} обучений"
        )

        return {
            "status": "success",
            "sessions": len(upcoming_sessions),
            "notifications": total_notifications,
            "results": notification_results,
        }

    except Exception as e:
        logger.error(f"[Обучения] Critical error checking upcoming studies: {e}")
        return {"status": "error", "message": str(e)}


async def send_study_notifications(
    sessions: List[StudySession], session_pool, bot: Bot
) -> dict:
    """Send notifications to study participants

    Args:
        sessions: List of upcoming study sessions
        session_pool: Database session pool
        bot: Bot instance

    Returns:
        Dict with notification results per session
    """
    notification_results = {}

    async with session_pool() as session:
        stp_repo = MainRequestsRepo(session)

        for session_obj in sessions:
            session_key = f"{session_obj.date.strftime('%d.%m.%Y')}_{session_obj.title}"
            notifications_sent = 0

            # Get unique participant names (avoid duplicates)
            # Only extract names from the ФИО field (column 2) - these are the actual participants
            # The РГ field (column 3) contains heads/supervisors who should NOT be notified
            participant_names: Set[str] = set()
            for area, name, rg, attendance, reason in session_obj.participants:
                # Add name from ФИО field (column 2) - actual participants
                if name and name.strip():
                    participant_names.add(name.strip())

            logger.debug(
                f"[Обучения] Проверяем обучение: {session_obj.title} на {session_obj.date.strftime('%d.%m.%Y')}"
            )
            logger.debug(
                f"[Обучения] Найдено {len(participant_names)} уникальных участников: {list(participant_names)}"
            )

            # Send notification to each participant
            for participant_name in participant_names:
                try:
                    # Find participant in database
                    participant = await stp_repo.employee.get_user(
                        fullname=participant_name
                    )

                    if not participant:
                        logger.warning(
                            f"[Обучения] Участник '{participant_name}' не найден в БД"
                        )
                        continue

                    if not participant.user_id:
                        logger.warning(
                            f"[Обучения] Участник '{participant_name}' найден в БД, но не имеет user_id"
                        )
                        continue

                    # Calculate time difference to determine notification type
                    time_diff = session_obj.date - datetime.now()

                    # Create notification message
                    message = await create_study_notification_message(
                        session_obj, stp_repo, time_diff
                    )

                    # Send notification
                    success = await send_message(bot, participant.user_id, message)

                    if success:
                        notifications_sent += 1
                        logger.debug(
                            f"[Обучения] {participant_name} уведомлен о скором обучении"
                        )
                    else:
                        logger.warning(
                            f"[Обучения] Ошибка уведомления {participant_name}"
                        )

                except Exception as e:
                    logger.error(
                        f"[Обучения] Error notifying participant {participant_name}: {e}"
                    )
                    continue

            notification_results[session_key] = notifications_sent
            logger.info(
                f"[Обучения] Обучение {session_key}: отправлено {notifications_sent} уведомлений"
            )

    return notification_results


async def create_study_notification_message(
    session: StudySession, stp_repo, time_diff: timedelta
) -> str:
    """Create notification message for study participant

    Args:
        session: Study session object
        stp_repo: Repository for database operations
        time_diff: Time difference until the session

    Returns:
        Formatted notification message
    """
    # Determine notification type based on time difference
    if abs(time_diff - timedelta(hours=2)) <= timedelta(minutes=10):
        # 2 hours before notification
        time_text = "через 2 часа"
    elif abs(time_diff - timedelta(hours=1)) <= timedelta(minutes=10):
        # 1 hour before notification
        time_text = "через 1 час"
    else:
        # Fallback (shouldn't happen with new logic)
        days_until = (session.date.date() - datetime.now().date()).days
        if days_until == 0:
            time_text = "сегодня"
        elif days_until == 1:
            time_text = "завтра"
        else:
            time_text = f"через {days_until} дн."

    # Get trainer information from database
    trainer_text = session.trainer
    if session.trainer:
        try:
            trainer_user = await stp_repo.employee.get_user(fullname=session.trainer)
            if trainer_user and trainer_user.username:
                trainer_text = (
                    f"<a href='t.me/{trainer_user.username}'>{session.trainer}</a>"
                )
        except Exception as e:
            logger.warning(
                f"[Обучения] Could not get trainer info for {session.trainer}: {e}"
            )

    message_parts = [
        "📚 <b>Напоминание об обучении</b>\n",
        f"Напоминаем, что <b>{time_text}</b> у тебя запланировано обучение:\n",
        f"📖 <b>Тема:</b> {session.title}",
        f"🎓 <b>Тренер:</b> {trainer_text}",
        f"\n📅 <b>Дата:</b> {session.date.strftime('%d.%m.%Y')} {session.time} {f'({session.duration})' if session.duration else ''}",
    ]

    message_parts.extend([
        "\n<blockquote expandable>💡 <b>Правила посещения обучений</b>",
        "• Подтверди или отклони явку в письме об обучении на почте",
        "• Крайний срок предупреждения о неявке - за 2 часа до начала обучения с линии",
        "• Обязательно наличие камеры</blockquote>",
    ])

    return "\n".join(message_parts)


def format_studies_notification_summary(sessions: List[StudySession]) -> str:
    """Format brief summary of upcoming studies for logs

    Args:
        sessions: List of upcoming study sessions

    Returns:
        Brief summary string
    """
    if not sessions:
        return "No upcoming studies found"

    summary_parts = [f"Upcoming studies: {len(sessions)}"]

    # Group by date
    dates = {}
    for session in sessions:
        date_str = session.date.strftime("%d.%m.%Y")
        if date_str not in dates:
            dates[date_str] = 0
        dates[date_str] += 1

    for date_str, count in dates.items():
        summary_parts.append(f"• {date_str}: {count} session(s)")

    return ", ".join(summary_parts)

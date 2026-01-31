"""HR scheduler for personnel processes."""

import logging
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from stp_database.models.STP import Employee
from stp_database.repo.STP import MainRequestsRepo
from stp_database.repo.STP.employee import EmployeeRepo

from tgbot.services.broadcaster import send_message
from tgbot.services.schedulers.base import BaseScheduler

logger = logging.getLogger(__name__)

MONTH_MAP = {
    "янв": 1,
    "фев": 2,
    "мар": 3,
    "апр": 4,
    "май": 5,
    "июн": 6,
    "июл": 7,
    "авг": 8,
    "сен": 9,
    "окт": 10,
    "ноя": 11,
    "дек": 12,
}

# Roman numerals for month matching in file names
ROMAN_MONTHS = [
    "I",
    "II",
    "III",
    "IV",
    "V",
    "VI",
    "VII",
    "VIII",
    "IX",
    "X",
    "XI",
    "XII",
]


class HRScheduler(BaseScheduler):
    """HR tasks scheduler."""

    def __init__(self):
        super().__init__("HR")

    def setup_jobs(self, scheduler: AsyncIOScheduler, stp_session_pool, bot: Bot):
        # Process fired users
        scheduler.add_job(
            func=self._fired_job,
            args=[stp_session_pool, bot],
            trigger="cron",
            id="hr_fired",
            name="Обработка увольнений",
            hour=9,
            minute=0,
        )
        scheduler.add_job(
            func=self._fired_job,
            args=[stp_session_pool, bot],
            trigger="date",
            id="hr_fired_startup",
            name="Запуск: Обработка увольнений",
            run_date=None,
        )

        # Notify unauthorized users
        self._add_job(
            scheduler,
            self._unauth_job,
            "cron",
            "notify_unauth",
            "Уведомления о неавторизованных",
            hour=10,
            minute=30,
            args=[stp_session_pool, bot],
        )

        # Process vacations
        scheduler.add_job(
            func=self._vacation_job,
            args=[stp_session_pool],
            trigger="cron",
            id="hr_vacation",
            name="Обработка отпусков",
            hour=9,
            minute=0,
        )
        scheduler.add_job(
            func=self._vacation_job,
            args=[stp_session_pool],
            trigger="date",
            id="hr_vacation_startup",
            name="Запуск: Обработка отпусков",
            run_date=None,
        )

    async def _fired_job(self, stp_session_pool, bot):
        await self._run_wrapped(process_fired_users, stp_session_pool, bot)

    async def _unauth_job(self, stp_session_pool, bot):
        await self._run_wrapped(notify_unauthorized_users, stp_session_pool, bot)

    async def _vacation_job(self, stp_session_pool):
        await self._run_wrapped(process_vacation_status, stp_session_pool)

    async def _run_wrapped(self, func, *args):
        name = func.__name__
        self._log_job_execution(name, True)
        try:
            await func(*args)
            self._log_job_execution(name, True)
        except Exception as e:
            self._log_job_execution(name, False, str(e))


def parse_dismissal_date(date_str: str) -> datetime:
    """Parse dismissal date from '04.авг' format."""
    parts = date_str.strip().split(".")
    if len(parts) != 2:
        raise ValueError(f"Invalid date format: {date_str}")
    day, month_str = int(parts[0]), parts[1].lower()
    if month_str not in MONTH_MAP:
        raise ValueError(f"Unknown month: {month_str}")
    return datetime(datetime.now().year, MONTH_MAP[month_str], day)


def get_fired_users(files_list: List[str] = None) -> List[str]:
    """Get fired users from Excel files."""
    fired = []
    uploads = Path("uploads")
    if not uploads.exists():
        logger.warning("[Увольнения] uploads not found")
        return fired

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    schedule_files = _find_schedule_files(uploads, files_list)

    for file_path in schedule_files:
        try:
            df = pd.read_excel(file_path, sheet_name="ЗАЯВЛЕНИЯ", header=None)
            for idx in range(len(df)):
                try:
                    fullname = str(df.iloc[idx, 0]) if pd.notna(df.iloc[idx, 0]) else ""
                    date_val = df.iloc[idx, 1] if pd.notna(df.iloc[idx, 1]) else None
                    type_val = str(df.iloc[idx, 2]) if pd.notna(df.iloc[idx, 2]) else ""

                    if (
                        type_val.strip().lower() in ["увольнение", "декрет"]
                        and fullname
                        and date_val
                        and date_val < today
                    ):
                        fired.append(fullname.strip())
                except Exception:
                    continue
        except Exception:
            continue

    logger.info(f"[Увольнения] Found {len(fired)} users")
    return fired


def _find_schedule_files(
    uploads: Path, files_list: List[str] = None, month_only: bool = False
) -> List[Path]:
    """Find schedule files.

    Args:
        uploads: Base uploads directory
        files_list: Optional list of file names to match
        month_only: If True, only return files for current month (e.g., "ГРАФИК * I 2026")
    """
    if files_list:
        files = []
        for file_name in files_list:
            for root, _, names in os.walk(uploads, followlinks=True):
                for name in names:
                    if Path(name).match(file_name):
                        files.append(Path(root) / name)
        return files

    if month_only:
        current_year = datetime.now().year
        current_month_idx = datetime.now().month - 1  # 0-indexed
        roman_month = ROMAN_MONTHS[current_month_idx]
        # Match files like "ГРАФИК * I 2026" or "ГРАФИК * I 2026.xlsx"
        year_pattern = str(current_year)
        files = []
        for root, _, names in os.walk(uploads, followlinks=True):
            for name in names:
                if name.startswith("ГРАФИК") and name.endswith(".xlsx"):
                    # Check if file contains current year and roman month
                    if roman_month in name and year_pattern in name:
                        files.append(Path(root) / name)
        return files

    return [
        Path(root) / name
        for root, _, names in os.walk(uploads, followlinks=True)
        for name in names
        if name.startswith("ГРАФИК") and name.endswith(".xlsx")
    ]


async def process_fired_users(
    stp_session_pool: async_sessionmaker[AsyncSession], bot: Bot = None
):
    """Process fired users - delete from DB and groups."""
    fired = get_fired_users()
    if not fired:
        return

    async with stp_session_pool() as session:
        repo = EmployeeRepo(session)
        total = 0
        for name in fired:
            deleted = await repo.delete_user(name)
            total += deleted or 0
        logger.info(f"[Увольнения] Deleted {total} records for {len(fired)} users")

    if bot and fired:
        await remove_from_groups(stp_session_pool, bot, fired)


async def remove_from_groups(
    stp_session_pool: async_sessionmaker[AsyncSession], bot: Bot, fired: List[str]
):
    """Remove fired users from groups with remove_unemployed=True."""
    async with stp_session_pool() as session:
        repo = MainRequestsRepo(session)

        for fullname in fired:
            employee = await repo.employee.get_users(fullname=fullname)
            if not employee or not employee.user_id:
                continue

            groups = await repo.group_member.get_member_groups(employee.user_id)
            for gm in groups:
                group = await repo.group.get_groups(gm.group_id)
                if not group or not group.remove_unemployed:
                    continue

                if await repo.group_member.remove_member(gm.group_id, employee.user_id):
                    try:
                        await bot.ban_chat_member(
                            chat_id=gm.group_id, user_id=employee.user_id
                        )
                        chat = await bot.get_chat(gm.group_id)
                        await bot.send_message(
                            employee.user_id,
                            f"✋ Ты был исключен из {'группы' if group.group_type == 'group' else 'канала'} <code>{chat.title}</code>",
                        )
                    except Exception as e:
                        logger.warning(f"[Увольнения] Failed to ban {fullname}: {e}")


async def notify_unauthorized_users(
    stp_session_pool: async_sessionmaker[AsyncSession], bot: Bot
) -> Dict:
    """Notify supervisors about unauthorized users."""
    async with stp_session_pool() as session:
        repo = MainRequestsRepo(session)
        unauthorized = await repo.employee.get_unauthorized_users()

    if not unauthorized:
        return {}

    by_head = _group_by_head(unauthorized)
    results = {}

    for head_name, subs in by_head.items():
        supervisor = await repo.employee.get_users(fullname=head_name)
        if not supervisor or not supervisor.user_id:
            continue

        msg = _create_notification_message(head_name, subs)
        results[head_name] = await send_message(bot, supervisor.user_id, msg)

    return results


def _group_by_head(users: List[Employee]) -> Dict[str, List]:
    """Group users by supervisor."""
    grouped = defaultdict(list)
    for user in users:
        if user.head and "@ertelecom.ru" not in user.head:
            grouped[user.head].append(user)
    return dict(grouped)


def _create_notification_message(head_name: str, subs: List) -> str:
    """Create notification message."""
    lines = [
        "🔔 <b>Неавторизованные сотрудники</b>",
        f"Привет, <b>{head_name}</b>!",
        f"В твоей группе обнаружено <b>{len(subs)}</b> неавторизованных сотрудника(ов):",
    ]
    for i, sub in enumerate(subs, 1):
        lines.append(f"{i}. <b>{sub.fullname}</b>")
        if sub.position and sub.division:
            lines.append(f"💼 {sub.position} {sub.division}")

    lines.extend([
        "\n💡 <b>Что нужно сделать:</b>",
        "• Попроси сотрудников авторизоваться в @stpsher_bot",
        "\n📋 <b>Для авторизации:</b>",
        "1️⃣ Перейти в @stpsher_bot",
        "2️⃣ Нажать /start",
        "3️⃣ Следовать инструкциям",
    ])
    return "\n".join(lines)


def get_vacation_users(files_list: List[str] = None) -> List[str]:
    """Get users on vacation from current month Excel files only."""
    from tgbot.services.files_processing.core.excel import ExcelReader

    users = []
    uploads = Path("uploads")
    if not uploads.exists():
        return users

    today = datetime.now()
    # Only check current month files to avoid checking old/future schedules
    schedule_files = _find_schedule_files(uploads, files_list, month_only=True)

    for file_path in schedule_files:
        try:
            reader = ExcelReader(file_path, "ГРАФИК")
            col = reader.find_date_column(today)
            if col is None:
                continue

            for fullname in reader.extract_all_users():
                row = reader.find_user_row(fullname)
                if row and reader.get_cell(row, col).strip().lower() in [
                    "отпуск",
                    "отпуск бс",
                ]:
                    users.append(fullname)
        except Exception:
            continue

    return users


async def process_vacation_status(stp_session_pool: async_sessionmaker[AsyncSession]):
    """Update vacation status in database."""
    on_vacation = get_vacation_users()

    async with stp_session_pool() as session:
        repo = EmployeeRepo(session)
        all_employees = await repo.get_users()

        set_on = 0
        set_off = 0
        processed = set()

        for name in on_vacation:
            processed.add(name)
            emp = await repo.get_users(fullname=name)
            if emp and not emp.on_vacation:
                emp.on_vacation = True
                set_on += 1

        for emp in all_employees:
            if emp.on_vacation and emp.fullname not in processed:
                emp.on_vacation = False
                set_off += 1

        await session.commit()
        logger.info(f"[Отпуска] Set on: {set_on}, set off: {set_off}")

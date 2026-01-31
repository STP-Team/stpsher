"""Achievement and rewards scheduler."""

import json
import logging
import time
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Dict, List

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from stp_database.models.STP.transactions import Transaction
from stp_database.repo.Stats.requests import StatsRequestsRepo
from stp_database.repo.STP import MainRequestsRepo

from tgbot.config import IS_DEVELOPMENT
from tgbot.services.broadcaster import send_message
from tgbot.services.schedulers.base import BaseScheduler

logger = logging.getLogger(__name__)

KPI_MAP = {
    "CSAT": ("csat", False), "CSAT_HIGH_RATED": ("csat_high_rated", False),
    "CSAT_RATED": ("csat_rated", False), "AHT": ("aht", False),
    "CC": ("contacts_count", False), "FLR": ("flr", False),
    "CSI": ("csi", False), "POK": ("pok", False),
    "DELAY": ("delay", False), "SalesCount": ("sales", False),
    "SalesPotential": ("sales_potential", False), "SalesConversion": ("sales_conversion", False),
    "PaidServiceCount": ("services", False), "PaidServiceConversion": ("services_conversion", False),
    "GOK": ("gok", True),
}


class Period(Enum):
    """Achievement check periods."""
    DAILY = ("d", "spec_day_kpi", 1, "daily")
    WEEKLY = ("w", "spec_week_kpi", 7, "weekly")
    MONTHLY = ("m", "spec_month_kpi", 30, "monthly")

    def __init__(self, code, method, days, desc):
        self.code = code
        self.method = method
        self.days = days
        self.desc = desc


class AchievementScheduler(BaseScheduler):
    """Achievement scheduler."""

    def __init__(self):
        super().__init__("Достижения")

    def setup_jobs(self, scheduler: AsyncIOScheduler, stp_pool: async_sessionmaker[AsyncSession],
                   stats_pool: async_sessionmaker[AsyncSession], bot: Bot):
        if IS_DEVELOPMENT:
            logger.info("[Achievements] Skipping scheduler setup in development mode")
            return

        for p in Period:
            scheduler.add_job(
                func=self._check_job, args=[stp_pool, stats_pool, bot, p],
                trigger="interval", id=f"achievements_{p.name.lower()}",
                name=f"Проверка {p.desc} достижений", hours=12,
                coalesce=True, misfire_grace_time=300, replace_existing=True,
            )
            scheduler.add_job(
                func=self._check_job, args=[stp_pool, stats_pool, bot, p],
                trigger="date", id=f"achievements_startup_{p.name.lower()}",
                name=f"Запуск: Проверка {p.desc} достижений", run_date=None,
            )

    async def _check_job(self, stp_pool, stats_pool, bot, period):
        start = time.time()
        self._log_job_execution(f"Проверка {period.desc} достижений", True)
        try:
            stats = await check_achievements(stp_pool, stats_pool, bot, period)
            dur = time.time() - start
            logger.info(f"[Achievements] {period.desc} check: {dur:.2f}s, users: {stats['users']}, awarded: {stats['awarded']}, errors: {stats['errors']}")
            self._log_job_execution(f"Проверка {period.desc} достижений", True)
        except Exception as e:
            self._log_job_execution(f"Проверка {period.desc} достижений", False, str(e))


async def check_achievements(stp_pool: async_sessionmaker[AsyncSession], stats_pool: async_sessionmaker[AsyncSession],
                             bot: Bot, period: Period) -> Dict:
    """Check and award achievements."""
    stats = {"users": 0, "awarded": 0, "errors": 0}

    async with (stp_pool() as stp_sess, stats_pool() as stats_sess):
        stp_repo, stats_repo = MainRequestsRepo(stp_sess), StatsRequestsRepo(stats_sess)

        users = await stp_repo.employee.get_users(roles=[1, 3, 10])
        if not users:
            return stats

        all_achievements = await stp_repo.achievement.get_achievements()
        period_achievements = [a for a in all_achievements if a.period == period.code]

        if not period_achievements:
            return stats

        logger.info(f"[Achievements] Checking {len(period_achievements)} {period.desc} for {len(users)} users")

        for user in users:
            try:
                stats["users"] += 1
                earned = await _check_user(stp_repo, stats_repo, user, period_achievements, period)
                if earned:
                    await _award(stp_repo, user, earned, bot)
                    stats["awarded"] += len(earned)
            except Exception as e:
                stats["errors"] += 1
                logger.error(f"[Achievements] Error for {user.fullname}: {e}")

        logger.info(f"[Achievements] Awarded {stats['awarded']} {period.desc} achievements")
    return stats


async def _check_user(stp_repo: MainRequestsRepo, stats_repo: StatsRequestsRepo, user,
                      achievements: List, period: Period) -> List[Dict]:
    """Check achievements for a user."""
    if not user.user_id:
        return []

    kpi_method = getattr(stats_repo, period.method, None)
    if not kpi_method:
        return []

    user_kpi = await kpi_method.get_kpi(user.employee_id)
    if not user_kpi or not user_kpi.extraction_period:
        return []

    extraction = user_kpi.extraction_period.date() if isinstance(user_kpi.extraction_period, datetime) else user_kpi.extraction_period
    user_premium = await stats_repo.spec_premium.get_premium(user.employee_id, extraction)

    existing, recent = await _get_history(stp_repo, user.user_id, extraction, period.days)
    existing_ids = {t.source_id for t in existing if t.source_id}
    recent_ids = {t.source_id for t in recent if t.source_id}

    earned = []
    for ach in achievements:
        if ach.id in existing_ids or ach.id in recent_ids:
            continue
        if not _matches_criteria(user, ach):
            continue
        if _check_kpi(user_kpi, ach.kpi, user_premium):
            earned.append({
                "id": ach.id, "name": ach.name, "description": ach.description,
                "reward": ach.reward, "kpi_values": _get_kpi_values(user_kpi, ach.kpi, user_premium),
                "extraction": extraction,
            })
            logger.info(f"[Achievements] {user.fullname} earned '{ach.name}'")

    return earned


async def _get_history(stp_repo: MainRequestsRepo, user_id: int, extraction, days: int):
    """Get user achievement history."""
    existing = await _get_by_kpi_date(stp_repo, user_id, extraction)
    cutoff = date.today() - timedelta(days=days)
    recent = await _get_recent(stp_repo, user_id, cutoff)
    return existing, recent


async def _get_by_kpi_date(stp_repo: MainRequestsRepo, user_id: int, extraction):
    query = select(Transaction).filter(
        and_(Transaction.user_id == user_id, Transaction.source_type == "achievement", Transaction.kpi_extracted_at == extraction)
    )
    result = await stp_repo.session.execute(query)
    return result.scalars().all()


async def _get_recent(stp_repo: MainRequestsRepo, user_id: int, cutoff: date):
    query = select(Transaction).filter(
        and_(Transaction.user_id == user_id, Transaction.source_type == "achievement", func.date(Transaction.created_at) >= cutoff)
    )
    result = await stp_repo.session.execute(query)
    return result.scalars().all()


def _matches_criteria(user, ach) -> bool:
    """Check if user matches achievement criteria."""
    if ach.division == "ALL":
        return True
    if ach.division == "НЦК":
        return user.division == "НЦК"
    if ach.division == "НТП":
        return user.division in ["НТП1", "НТП2"]
    if ach.division != user.division:
        return False
    return ach.position == "ALL" or user.position == ach.position


def _check_kpi(user_kpi, kpi_str: str, user_premium=None) -> bool:
    """Check if KPI matches criteria."""
    try:
        criteria = json.loads(kpi_str)
        for kpi_name, (min_val, max_val) in criteria.items():
            val = _get_kpi_value(user_kpi, kpi_name, user_premium)
            if val is None or not (min_val <= val <= max_val):
                return False
        return True
    except Exception:
        return False


def _get_kpi_value(user_kpi, kpi_name: str, user_premium=None):
    """Get KPI value by name."""
    if kpi_name not in KPI_MAP:
        return None
    attr, from_premium = KPI_MAP[kpi_name]
    if from_premium and user_premium is not None:
        val = getattr(user_premium, attr, None)
        if val is not None:
            return val
    return getattr(user_kpi, attr, None)


def _get_kpi_values(user_kpi, kpi_str: str, user_premium=None) -> Dict:
    """Get all KPI values from criteria."""
    values = {}
    try:
        criteria = json.loads(kpi_str)
        for kpi_name in criteria.keys():
            val = _get_kpi_value(user_kpi, kpi_name, user_premium)
            if val is not None:
                display = kpi_name
                for k, (a, _) in KPI_MAP.items():
                    if a == kpi_name:
                        display = k
                        break
                values[display] = val
    except Exception:
        pass
    return values


async def _award(stp_repo: MainRequestsRepo, user, achievements: List[Dict], bot: Bot):
    """Award achievements to user."""
    successful = []
    total_reward = 0
    balance = None

    for ach in achievements:
        kpi_str = _format_kpi(ach["kpi_values"])
        comment = f'Достижение "{ach["name"]}". Показатель: {kpi_str}'

        txn, new_bal = await stp_repo.transaction.add_transaction(
            user_id=user.user_id, transaction_type="earn", source_type="achievement",
            amount=ach["reward"], source_id=ach["id"], comment=comment, kpi_extracted_at=ach.get("extraction"),
        )

        if txn:
            successful.append(ach)
            total_reward += ach["reward"]
            balance = new_bal

    if successful:
        msg = _create_msg(successful, total_reward, balance)
        await send_message(bot, user.user_id, msg)


def _format_kpi(values: Dict) -> str:
    """Format KPI values as string."""
    parts = []
    for name, val in values.items():
        if val is not None:
            formatted = str(int(val)) if isinstance(val, float) and val.is_integer() else f"{val:g}"
            parts.append(f"{name} {formatted}")
    return ", ".join(parts)


def _create_msg(achievements: List[Dict], total: int, balance: int = None) -> str:
    """Create achievement notification message."""
    if len(achievements) == 1:
        ach = achievements[0]
        lines = [f"🏆 <b>Новое достижение!</b>", f"🎉 <b>{ach['name']}: {ach['reward']} баллов</b>"]
        if ach.get("kpi_values"):
            lines.append(f"📊 Твои показатели: {_format_kpi(ach['kpi_values'])}")
        if balance is not None:
            lines.append(f"💎 Новый баланс: {balance} баллов")
        lines.append("✨ Поздравляем!")
        return "\n".join(lines)

    lines = [f"🏆 <b>Получено достижений: {len(achievements)}</b>"]
    for i, ach in enumerate(achievements, 1):
        lines.append(f"{i}. 🎉 <b>{ach['name']}</b> (+{ach['reward']} баллов)")
        if ach.get("description"):
            lines.append(f"   📝 {ach['description']}")
        if ach.get("kpi_values"):
            lines.append(f"   📊 {_format_kpi(ach['kpi_values'])}")
        lines.append("")

    lines.append(f"💰 <b>Общая награда: {total} баллов</b>")
    if balance is not None:
        lines.append(f"💎 Текущий баланс: {balance} баллов")
    lines.append("✨ Поздравляем!")

    return "\n".join(lines)

"""
Public API functions for backward compatibility.
"""

from datetime import datetime
from typing import Dict, List

from infrastructure.database.repo.requests import RequestsRepo
from .managers import MonthManager
from .parsers import ScheduleParser
from .duty_parser import DutyScheduleParser
from .head_parser import HeadScheduleParser
from .models import ScheduleType


def get_user_schedule(fullname: str, month: str, division: str) -> Dict[str, str]:
    """Get user schedule (backward compatibility function)"""
    parser = ScheduleParser()
    return parser.get_user_schedule(fullname, month, division)


def get_user_schedule_formatted(
    fullname: str, month: str, division: str, compact: bool = False
) -> str:
    """Get formatted user schedule (backward compatibility function)"""
    parser = ScheduleParser()
    return parser.get_user_schedule_formatted(fullname, month, division, compact)


def get_duties_schedule(
    fullname: str, month: str, division: str, compact: bool = False
) -> str:
    """Get duties schedule for user"""
    parser = ScheduleParser()
    return parser.get_user_schedule_formatted(
        fullname, month, division, compact, ScheduleType.DUTIES
    )


def get_heads_schedule(
    fullname: str, month: str, division: str, compact: bool = False
) -> str:
    """Get heads schedule"""
    parser = ScheduleParser()
    return parser.get_user_schedule_formatted(
        fullname, month, division, compact, ScheduleType.HEADS
    )


def get_available_months() -> List[str]:
    """Get list of available months"""
    return MonthManager.get_available_months()


async def get_duties_for_current_date(division: str, stp_repo: RequestsRepo) -> str:
    """Get duties for current date"""
    parser = DutyScheduleParser()
    current_date = parser.get_current_yekaterinburg_date()
    duties = await parser.get_duties_for_date(current_date, division, stp_repo)
    return parser.format_duties_for_date(current_date, duties)


async def get_duties_for_date(
    date: datetime, division: str, stp_repo: RequestsRepo
) -> str:
    """Get duties for specified date"""
    parser = DutyScheduleParser()
    duties = await parser.get_duties_for_date(date, division, stp_repo)
    return parser.format_duties_for_date(date, duties)


async def get_heads_for_current_date(division: str, stp_repo: RequestsRepo) -> str:
    """Get heads for current date"""
    parser = HeadScheduleParser()
    current_date = parser.get_current_yekaterinburg_date()
    heads = await parser.get_heads_for_date(current_date, division, stp_repo)
    return parser.format_heads_for_date(current_date, heads)


async def get_heads_for_date(
    date: datetime, division: str, stp_repo: RequestsRepo
) -> str:
    """Get heads for specified date"""
    parser = HeadScheduleParser()
    heads = await parser.get_heads_for_date(date, division, stp_repo)
    return parser.format_heads_for_date(date, heads)

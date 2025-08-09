"""
Data models for schedule operations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ScheduleType(Enum):
    """Types of schedules"""

    REGULAR = "regular"
    DUTIES = "duties"
    HEADS = "heads"


@dataclass
class DayInfo:
    """Information about a day in schedule"""

    day: str
    schedule: str
    work_hours: int = 0

    @property
    def day_number(self) -> int:
        """Extract day number"""
        try:
            return int(self.day.split()[0])
        except (ValueError, IndexError):
            return 0


@dataclass
class ScheduleStats:
    """Schedule statistics"""

    total_work_days: int
    total_work_hours: float
    vacation_days: int
    sick_days: int
    days_off: int
    missing_days: int
    total_days: int


@dataclass
class DutyInfo:
    """Duty information"""

    name: str
    schedule: str
    shift_type: str  # "П" или "С" или ""
    work_hours: str


@dataclass
class HeadInfo:
    """Head of group information"""

    name: str
    chat_id: int
    schedule: str
    duty_info: Optional[str] = None


# File: tgbot/services/schedule/exceptions.py
"""
Custom exceptions for schedule operations.
"""


class ScheduleError(Exception):
    """Base exception for schedule errors"""

    pass


class ScheduleFileNotFoundError(ScheduleError):
    """Schedule file not found"""

    pass


class UserNotFoundError(ScheduleError):
    """User not found in schedule"""

    pass


class MonthNotFoundError(ScheduleError):
    """Month not found in file"""

    pass


class InvalidDataError(ScheduleError):
    """Invalid data in file"""

    pass

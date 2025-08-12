"""
Schedule services package for parsing and formatting various types of schedules.
"""

from .exceptions import (
    ScheduleError,
    ScheduleFileNotFoundError,
    UserNotFoundError,
    MonthNotFoundError,
    InvalidDataError,
)
from .formatters import ScheduleFormatter
from .managers import MonthManager, ScheduleFileManager
from .models import (
    DayInfo,
    DutyInfo,
    HeadInfo,
    ScheduleStats,
)
from .parsers import ScheduleParser, DutyScheduleParser, HeadScheduleParser

__all__ = [
    # Core classes
    "ScheduleParser",
    "DutyScheduleParser",
    "HeadScheduleParser",
    "ScheduleFormatter",
    "ScheduleFileManager",
    "MonthManager",
    # Models
    "DayInfo",
    "DutyInfo",
    "HeadInfo",
    "ScheduleStats",
    # Exceptions
    "ScheduleError",
    "ScheduleFileNotFoundError",
    "UserNotFoundError",
    "MonthNotFoundError",
    "InvalidDataError",
]

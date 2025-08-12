"""
Schedule services package for parsing and formatting various types of schedules.
"""

from .Exceptions import (
    ScheduleError,
    ScheduleFileNotFoundError,
    UserNotFoundError,
    MonthNotFoundError,
    InvalidDataError,
)
from .duty_parser import DutyScheduleParser
from .formatters import ScheduleFormatter
from .head_parser import HeadScheduleParser
from .managers import MonthManager, ScheduleFileManager
from .models import (
    DayInfo,
    DutyInfo,
    HeadInfo,
    ScheduleStats,
)
from .parsers import ScheduleParser

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

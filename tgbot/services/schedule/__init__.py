"""Schedule services package for parsing and formatting various types of schedules."""

from .exceptions import (
    InvalidDataError,
    MonthNotFoundError,
    ScheduleError,
    ScheduleFileNotFoundError,
    UserNotFoundError,
)
from .formatters import ScheduleFormatter
from .managers import MonthManager, ScheduleFileManager
from .models import (
    DayInfo,
    DutyInfo,
    HeadInfo,
    ScheduleStats,
)
from .parsers import DutyScheduleParser, HeadScheduleParser, ScheduleParser

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

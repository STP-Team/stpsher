"""
Schedule services package for parsing and formatting various types of schedules.
"""

# Public API functions for backward compatibility
from .api import (
    get_available_months,
    get_duties_for_current_date,
    get_duties_for_date,
    get_duties_schedule,
    get_heads_for_current_date,
    get_heads_for_date,
    get_heads_schedule,
    get_user_schedule,
    get_user_schedule_formatted,
)
from .duty_parser import DutyScheduleParser
from .formatters import ScheduleFormatter
from .head_parser import HeadScheduleParser
from .managers import MonthManager, ScheduleFileManager
from .models import (
    DayInfo,
    DutyInfo,
    HeadInfo,
    InvalidDataError,
    MonthNotFoundError,
    ScheduleError,
    ScheduleFileNotFoundError,
    ScheduleStats,
    ScheduleType,
    UserNotFoundError,
)
from .parsers import ScheduleParser
from .utils import ScheduleUtils

__all__ = [
    # Core classes
    "ScheduleParser",
    "DutyScheduleParser",
    "HeadScheduleParser",
    "ScheduleFormatter",
    "ScheduleFileManager",
    "MonthManager",
    "ScheduleUtils",
    # Models
    "ScheduleType",
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
    # Public API
    "get_user_schedule",
    "get_user_schedule_formatted",
    "get_duties_schedule",
    "get_heads_schedule",
    "get_available_months",
    "get_duties_for_current_date",
    "get_duties_for_date",
    "get_heads_for_current_date",
    "get_heads_for_date",
]

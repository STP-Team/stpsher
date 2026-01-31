"""Time parsing utilities.

This module provides functions for parsing and validating time-related data
used across the files_processing package.
"""

import logging
import re
from datetime import datetime
from typing import Optional, Tuple

from ..core.constants import MONTH_NAMES_EN_TO_RU, MONTH_NAMES_TITLE

logger = logging.getLogger(__name__)

# Pre-compiled regex patterns for performance
TIME_PATTERN = re.compile(r"\d{1,2}:\d{2}-\d{1,2}:\d{2}")
DAY_HEADER_PATTERN = re.compile(r"^(\d{1,2})[А-Яа-я]{0,2}$")


def extract_day_number(day_str: str) -> int:
    """Extract day number from day string.

    Args:
        day_str: Day string (e.g., '15 (Пн)', '28Чт', '15')

    Returns:
        Day number or 0 if extraction fails

    Examples:
        >>> extract_day_number('15 (Пн)')
        15
        >>> extract_day_number('28Чт')
        28
        >>> extract_day_number('invalid')
        0
    """
    try:
        return int(day_str.split()[0])
    except (ValueError, IndexError):
        return 0


def is_time_format(text: str) -> bool:
    """Check if text matches time format HH:MM-HH:MM.

    Args:
        text: Text to check

    Returns:
        True if text contains time format, otherwise False
    """
    if not text:
        return False
    return bool(TIME_PATTERN.search(text.strip()))


def parse_time_range(time_str: str) -> Tuple[int, int]:
    """Parse time range string to start and end minutes.

    Args:
        time_str: Time range string (e.g., '09:00-18:00')

    Returns:
        Tuple of (start_minutes, end_minutes) from midnight

    Examples:
        >>> parse_time_range('09:00-18:00')
        (540, 1080)
        >>> parse_time_range('18:00-09:00')  # Night shift
        (1080, 1170)
    """
    try:
        if "-" not in time_str:
            return 0, 0

        start_time, end_time = time_str.split("-")
        start_parts = start_time.strip().split(":")
        end_parts = end_time.strip().split(":")

        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
        end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])

        # Handle night shifts (end time is next day)
        if end_minutes < start_minutes:
            end_minutes += 24 * 60

        return start_minutes, end_minutes

    except (ValueError, IndexError):
        return 0, 0


def calculate_work_hours(time_str: str) -> float:
    """Calculate work hours from time string.

    Args:
        time_str: Time range string (e.g., '09:00-18:00')

    Returns:
        Work hours as float

    Examples:
        >>> calculate_work_hours('09:00-18:00')
        9.0
        >>> calculate_work_hours('18:00-09:00')  # Night shift
        15.0
    """
    start_minutes, end_minutes = parse_time_range(time_str)
    if start_minutes == 0 and end_minutes == 0:
        return 0.0
    return (end_minutes - start_minutes) / 60.0


def get_current_day() -> int:
    """Get current day of month.

    Returns:
        Current day number (1-31)
    """
    return datetime.now().day


def get_current_month() -> str:
    """Get current month in Russian.

    Returns:
        Current month name in Russian (lowercase)
    """
    now = datetime.now()
    current_month_en = now.strftime("%B").lower()
    return MONTH_NAMES_EN_TO_RU.get(current_month_en, current_month_en)


def is_current_month(month: str) -> bool:
    """Check if given month is the current month.

    Args:
        month: Month name to check

    Returns:
        True if month is current month, otherwise False
    """
    return month.lower() == get_current_month()


def get_current_date() -> datetime:
    """Get current date and time.

    Returns:
        Current datetime
    """
    return datetime.now()


def get_duty_sheet_name(date: datetime) -> str:
    """Generate duty sheet name for given date.

    Args:
        date: Date to generate sheet name for

    Returns:
        Sheet name (e.g., 'Дежурство Январь')
    """
    month_name = MONTH_NAMES_TITLE[date.month - 1]
    return f"Дежурство {month_name}"


def parse_duty_entry(cell_value: str) -> Tuple[str, str]:
    """Parse duty entry to extract shift type and schedule.

    Args:
        cell_value: Cell value (e.g., 'П 09:00-18:00', 'С 18:00-09:00')

    Returns:
        Tuple of (shift_type, schedule)

    Examples:
        >>> parse_duty_entry('П 09:00-18:00')
        ('П', '09:00-18:00')
        >>> parse_duty_entry('С 18:00-09:00')
        ('С', '18:00-09:00')
    """
    if not cell_value or cell_value.strip() in ["", "nan", "None"]:
        return "", ""

    cell_value = cell_value.strip()

    if cell_value.startswith("П "):
        return "П", cell_value[2:].strip()
    elif cell_value.startswith("С "):
        return "С", cell_value[2:].strip()
    else:
        if is_time_format(cell_value):
            return "", cell_value
        else:
            return "", cell_value


def format_time_with_emoji(schedule: str, shift_type: Optional[str] = None) -> str:
    """Format schedule with shift type emoji.

    Args:
        schedule: Time schedule string
        shift_type: Optional shift type ('С' for senior, 'П' for helper)

    Returns:
        Formatted string with emoji
    """
    if shift_type == "С":
        return f"👮 {schedule}"
    elif shift_type == "П":
        return f"⚔️ {schedule}"
    return schedule

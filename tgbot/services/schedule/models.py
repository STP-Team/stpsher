"""
Data models for schedule operations.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DayInfo:
    """
    Информация о дне в графике
    """

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
    """
    Статистика графика
    """

    total_work_days: int
    total_work_hours: float
    vacation_days: int
    sick_days: int
    days_off: int
    missing_days: int
    total_days: int


@dataclass
class DutyInfo:
    """
    Информация о дежурном
    """

    name: str
    user_id: int
    username: str | None
    schedule: str
    shift_type: str  # "П" или "С" или ""
    work_hours: str


@dataclass
class HeadInfo:
    """
    Информация о руководителе группы
    """

    name: str
    user_id: int
    username: str | None
    schedule: str
    duty_info: Optional[str] = None

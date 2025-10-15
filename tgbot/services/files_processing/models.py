"""Data models for files_processing operations."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DayInfo:
    """Информация о дне в графике."""

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
    """Статистика графика"""

    total_work_days: int
    total_work_hours: float
    vacation_days: int
    sick_days: int
    days_off: int
    missing_days: int
    total_days: int


@dataclass
class DutyInfo:
    """Информация о дежурном"""

    name: str
    user_id: int
    username: str | None
    schedule: str
    shift_type: str  # "П" или "С" или ""
    work_hours: str


@dataclass
class HeadInfo:
    """Информация о руководителе группы"""

    name: str
    user_id: int
    username: str | None
    schedule: str
    duty_info: Optional[str] = None


@dataclass
class GroupMemberInfo:
    """Информация о сотруднике группы"""

    name: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    schedule: str = ""
    position: str = ""
    working_hours: str = ""
    duty_info: Optional[str] = None

    @property
    def display_name(self) -> str:
        if self.user_id:
            return f"<a href='tg://user?id={self.user_id}'>{self.name}</a>"
        return self.name

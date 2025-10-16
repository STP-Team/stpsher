"""Модели данных для процессинга графиков.

Модуль предоставляет dataclass модели для представления различных
элементов графиков работы.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class DayInfo:
    """Информация о дне в графике.

    Attributes:
        day: Строка с днем (например, "15 (Пн)")
        schedule: График работы
        work_hours: Количество рабочих часов
    """

    day: str
    schedule: str
    work_hours: int = 0

    @property
    def day_number(self) -> int:
        """Извлекает номер дня.

        Returns:
            Номер дня месяца (1-31), или 0 если не удалось извлечь
        """
        try:
            return int(self.day.split()[0])
        except (ValueError, IndexError):
            return 0


@dataclass(slots=True, frozen=True)
class ScheduleStats:
    """Статистика графика (immutable).

    Attributes:
        total_work_days: Всего рабочих дней
        total_work_hours: Всего рабочих часов
        vacation_days: Дней в отпуске
        sick_days: Дней на больничном
        days_off: Выходных дней
        missing_days: Дней отсутствия
        total_days: Всего дней в периоде
    """

    total_work_days: int
    total_work_hours: float
    vacation_days: int
    sick_days: int
    days_off: int
    missing_days: int
    total_days: int


@dataclass(slots=True)
class DutyInfo:
    """Информация о дежурном.

    Attributes:
        name: ФИО дежурного
        user_id: ID пользователя в Telegram
        username: Username в Telegram
        schedule: График дежурства (например, "09:00-18:00")
        shift_type: Тип смены ("П" - помощник, "С" - старший, "" - не указано)
        work_hours: Рабочие часы
    """

    name: str
    user_id: int
    username: Optional[str]
    schedule: str
    shift_type: str  # "П" или "С" или ""
    work_hours: str


@dataclass(slots=True)
class HeadInfo:
    """Информация о руководителе группы.

    Attributes:
        name: ФИО руководителя
        user_id: ID пользователя в Telegram
        username: Username в Telegram
        schedule: График работы
        duty_info: Информация о дежурстве (опционально)
    """

    name: str
    user_id: int
    username: Optional[str]
    schedule: str
    duty_info: Optional[str] = None


@dataclass(slots=True)
class GroupMemberInfo:
    """Информация о сотруднике группы.

    Attributes:
        name: ФИО сотрудника
        user_id: ID пользователя в Telegram
        username: Username в Telegram
        schedule: График работы
        position: Должность
        working_hours: Рабочие часы на конкретный день
        duty_info: Информация о дежурстве (опционально)
    """

    name: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    schedule: str = ""
    position: str = ""
    working_hours: str = ""
    duty_info: Optional[str] = None

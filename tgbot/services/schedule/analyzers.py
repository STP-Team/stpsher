import re
from typing import Any, Dict

from .models import DayInfo


class ScheduleAnalyzer:
    """
    Анализатор для расписаний
    """

    @staticmethod
    def categorize_schedule_entry(schedule_value: str) -> str:
        """
        Категория смены
        :param schedule_value: Значение клетки
        :return:
        """
        schedule_clean = schedule_value.strip().upper()

        if not schedule_clean or schedule_clean in ["НЕ УКАЗАНО", "NAN", "NONE", ""]:
            return "day_off"
        elif schedule_clean.lower() == "отпуск":
            return "vacation"
        elif schedule_clean.lower() == "отпуск бс":
            return "vacation_bs"
        elif schedule_clean.lower() == "в":
            return "army"
        elif any(word in schedule_clean for word in ["ЛНТС"]):
            return "sick"
        elif schedule_clean.lower() == "Н":
            return "missing"
        elif any(char in schedule_clean for char in ["-", ":"]):
            return "work"
        else:
            return "work"

    @staticmethod
    def calculate_work_hours(schedule: str) -> float:
        """Calculate work hours from schedule"""
        time_pattern = r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})"
        match = re.search(time_pattern, schedule)

        if not match:
            return 0.0

        start_hour, start_min, end_hour, end_min = map(int, match.groups())
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min

        if end_minutes < start_minutes:
            end_minutes += 24 * 60

        work_minutes = end_minutes - start_minutes
        work_hours = work_minutes / 60

        if work_hours >= 8:
            work_hours -= 1

        return round(work_hours, 1)

    @staticmethod
    def analyze_schedule(
        schedule_data: Dict[str, str],
    ) -> tuple[
        list[Any], list[Any], list[Any], list[Any], list[Any], list[Any], list[Any]
    ]:
        """Analyze schedule and categorize by type"""
        work_days = []
        days_off = []
        vacation_days = []
        vacation_bs_days = []
        army_days = []
        sick_days = []
        missing_days = []

        for day, schedule_value in schedule_data.items():
            category = ScheduleAnalyzer.categorize_schedule_entry(schedule_value)
            work_hours = (
                ScheduleAnalyzer.calculate_work_hours(schedule_value)
                if category == "work"
                else 0
            )

            day_info = DayInfo(day=day, schedule=schedule_value, work_hours=work_hours)

            if category == "work":
                work_days.append(day_info)
            elif category == "vacation":
                vacation_days.append(day_info)
            elif category == "vacation_bs":
                vacation_bs_days.append(day_info)
            elif category == "army":
                army_days.append(day_info)
            elif category == "sick":
                sick_days.append(day_info)
            elif category == "missing":
                missing_days.append(day_info)
            else:
                days_off.append(day_info)
            print(day, schedule_value, category)
        return (
            work_days,
            days_off,
            vacation_days,
            vacation_bs_days,
            army_days,
            sick_days,
            missing_days,
        )

"""Анализатор расписаний.

Модуль предоставляет функциональность для анализа и категоризации
записей расписания.
"""

import re
from typing import Dict, List, Tuple

from ..parsers.base import BaseParser
from .models import DayInfo


class ScheduleAnalyzer:
    """Анализатор для расписаний с поддержкой категоризации и расчета часов."""

    @staticmethod
    def categorize_schedule_entry(schedule_value: str) -> str:
        """Определяет категорию записи расписания.

        Args:
            schedule_value: Значение клетки расписания

        Returns:
            Категория: work, vacation, vacation_bs, army, sick, missing, или day_off
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
    def calculate_work_hours(time_str: str) -> float:
        """Рассчитывает рабочие часы по временному диапазону.

        Args:
            time_str: Строка временного диапазона (может содержать несколько диапазонов)

        Returns:
            Кол-во рабочих часов
        """
        if not time_str or not time_str.strip():
            return 0.0

        # Паттерн для поиска временных диапазонов
        time_pattern = r"\d{1,2}:\d{2}-\d{1,2}:\d{2}"
        time_ranges = re.findall(time_pattern, time_str)

        if not time_ranges:
            return 0.0

        total_work_minutes = 0

        # Обработать каждый временной диапазон
        for time_range in time_ranges:
            start_minutes, end_minutes = BaseParser.parse_time_range(time_range)

            if start_minutes == 0 and end_minutes == 0:
                continue

            work_minutes = end_minutes - start_minutes
            total_work_minutes += work_minutes

        # Конвертировать в часы
        work_hours = total_work_minutes / 60

        # Вычесть 1 час на обед только для одного непрерывного диапазона >= 8 часов
        # Если несколько диапазонов, обед уже учтен в промежутке между ними
        if len(time_ranges) == 1 and work_hours >= 8:
            work_hours -= 1

        return round(work_hours, 1)

    @staticmethod
    def analyze_schedule(
        schedule_data: Dict[str, str],
    ) -> Tuple[
        List[DayInfo],
        List[DayInfo],
        List[DayInfo],
        List[DayInfo],
        List[DayInfo],
        List[DayInfo],
        List[DayInfo],
    ]:
        """Анализирует расписание и категоризирует по типам.

        Args:
            schedule_data: Словарь с данными расписания {день: значение}

        Returns:
            Кортеж из 7 списков: (рабочие_дни, выходные, отпуск, отпуск_бс, военкомат, больничный, отсутствия)
        """
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
        return (
            work_days,
            days_off,
            vacation_days,
            vacation_bs_days,
            army_days,
            sick_days,
            missing_days,
        )

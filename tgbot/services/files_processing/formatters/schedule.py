"""Форматирование графиков.

Модуль предоставляет инструменты для форматирования расписаний
в компактном и детальном форматах.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from tgbot.misc.helpers import tz
from tgbot.services.files_processing.core.models import DayInfo

# Маппинг названий месяцев (Английский -> Русский)
MONTH_NAMES_MAP = {
    "january": "январь",
    "february": "февраль",
    "march": "март",
    "april": "апрель",
    "may": "май",
    "june": "июнь",
    "july": "июль",
    "august": "август",
    "september": "сентябрь",
    "october": "октябрь",
    "november": "ноябрь",
    "december": "декабрь",
}


def extract_day_number(day_str: str) -> int:
    """Извлекает номер дня из строки дня.

    Args:
        day_str: Строка дня (например, '15 (Пн)')

    Returns:
        Номер дня или 0 при ошибке
    """
    try:
        return int(day_str.split()[0])
    except (ValueError, IndexError):
        return 0


def is_current_month(month: str) -> bool:
    """Проверяет является ли указанный месяц текущим.

    Args:
        month: Название месяца

    Returns:
        True если месяц текущий, иначе False
    """
    now = datetime.now()
    current_month_en = now.strftime("%B").lower()
    current_month_ru = MONTH_NAMES_MAP.get(current_month_en, current_month_en)
    return month.lower() == current_month_ru


def get_current_day() -> int:
    """Получает текущий день месяца.

    Returns:
        Номер текущего дня
    """
    return datetime.now().day


def get_current_month() -> str:
    """Получает текущий месяц в русском формате.

    Returns:
        Название текущего месяца на русском языке
    """
    now = datetime.now()
    current_month_en = now.strftime("%B").lower()
    return MONTH_NAMES_MAP.get(current_month_en, current_month_en)


def get_current_date() -> datetime:
    """Получает текущую дату и время по Екатеринбургу.

    Returns:
        Текущая дата и время с учетом временной зоны
    """
    return datetime.now(tz)


class ScheduleFormatter:
    """Форматтер для расписаний с компактным и детальным режимами."""

    @staticmethod
    def format_compact(
        month: str,
        work_days: List[DayInfo],
        days_off: List[DayInfo],
        vacation_days: List[DayInfo],
        vacation_bs_days: List[DayInfo],
        army_days: List[DayInfo],
        sick_days: List[DayInfo],
        missing_days: List[DayInfo],
        current_day_duty: Optional[str] = None,
    ) -> str:
        """Компактный формат расписания.

        Args:
            month: Название месяца
            work_days: Список рабочих дней
            days_off: Список выходных дней
            vacation_days: Список дней отпуска
            vacation_bs_days: Список дней отпуска БС
            army_days: Список дней в военкомате
            sick_days: Список дней на больничном
            missing_days: Список дней отсутствия
            current_day_duty: Информация о дежурстве и купленных обменах на текущий день

        Returns:
            Отформатированная строка расписания
        """
        lines = [f"<b>👔 Мой график • {month.capitalize()}</b>"]

        # Check if we're viewing the current month
        viewing_current_month = is_current_month(month)
        effective_current_day = get_current_day() if viewing_current_month else None

        # Add today's schedule line if viewing current month
        if viewing_current_month:
            today_line = ScheduleFormatter._get_today_schedule_line(
                effective_current_day,
                work_days,
                days_off,
                vacation_days,
                vacation_bs_days,
                army_days,
                sick_days,
                missing_days,
                duty_info=current_day_duty,  # Pass duty info for today
            )
            if today_line:
                lines.append("")
                lines.append(today_line)

        lines.append("")

        if work_days:
            lines.append("🔸 <b>Рабочие:</b>")
            grouped_schedule = ScheduleFormatter._group_consecutive_schedule(
                work_days, effective_current_day
            )
            lines.extend(grouped_schedule)

        if vacation_days:
            vacation_range = ScheduleFormatter._format_day_range(
                [d.day for d in vacation_days], effective_current_day
            )
            lines.append(f"\n🏖 <b>Отпуск:</b> {vacation_range}")

        if vacation_bs_days:
            vacation_bs_range = ScheduleFormatter._format_day_range(
                [d.day for d in vacation_bs_days], effective_current_day
            )
            lines.append(f"\n🏖 <b>БС:</b> {vacation_bs_range}")

        if army_days:
            army_days_range = ScheduleFormatter._format_day_range(
                [d.day for d in army_days], effective_current_day
            )
            lines.append(f"\n🎖️ <b>Военкомат:</b> {army_days_range}")

        if sick_days:
            sick_range = ScheduleFormatter._format_day_range(
                [d.day for d in sick_days], effective_current_day
            )
            lines.append(f"\n🏥 <b>БЛ:</b> {sick_range}")

        if missing_days:
            missing_range = ScheduleFormatter._format_day_range(
                [d.day for d in missing_days], effective_current_day
            )
            lines.append(f"\n🕵️‍♂️ <b>Отсутствия:</b> {missing_range}")

        if days_off:
            if len(days_off) <= 3:
                days_str = ", ".join([
                    f"<u><b>{d.day.split()[0]}</b></u>"
                    if effective_current_day
                    and int(d.day.split()[0]) == effective_current_day
                    else d.day.split()[0]
                    for d in days_off
                ])
                lines.append(f"\n🏠 <b>Выходные:</b>\n{days_str}")
            else:
                off_range = ScheduleFormatter._format_day_range(
                    [d.day for d in days_off], effective_current_day
                )
                lines.append(f"\n🏠 <b>Выходные:</b>\n{off_range}")

        lines.append("\n<i>Перечисление указано в числах месяца</i>")
        return "\n".join(lines)

    @staticmethod
    def format_detailed(
        month: str,
        work_days: List[DayInfo],
        days_off: List[DayInfo],
        vacation_days: List[DayInfo],
        vacation_bs_days: List[DayInfo],
        army_days: List[DayInfo],
        sick_days: List[DayInfo],
        missing_days: List[DayInfo],
    ) -> str:
        """Детальный формат расписания.

        Args:
            month: Название месяца
            work_days: Список рабочих дней
            days_off: Список выходных дней
            vacation_days: Список дней отпуска
            vacation_bs_days: Список дней отпуска БС
            army_days: Список дней в военкомате
            sick_days: Список дней на больничном
            missing_days: Список дней отсутствия

        Returns:
            Отформатированная строка расписания с детальной информацией
        """
        lines = [f"<b>👔 Мой график • {month.capitalize()}</b>\n"]

        # Get current day
        current_day = get_current_day()

        all_days = []
        for day_info in work_days:
            all_days.append((day_info, "work"))
        for day_info in days_off:
            all_days.append((day_info, "day_off"))
        for day_info in vacation_days:
            all_days.append((day_info, "vacation"))
        for day_info in vacation_bs_days:
            all_days.append((day_info, "vacation_bs"))
        for day_info in army_days:
            all_days.append((day_info, "army"))
        for day_info in sick_days:
            all_days.append((day_info, "sick"))
        for day_info in missing_days:
            all_days.append((day_info, "missing"))

        all_days.sort(key=lambda x: extract_day_number(x[0].day))

        # Remove duplicates - prioritize entries with proper day formatting
        day_groups = {}
        for day_info, day_type in all_days:
            day_number = extract_day_number(day_info.day)
            if day_number > 0:  # Only process valid day numbers
                if day_number not in day_groups:
                    day_groups[day_number] = []
                day_groups[day_number].append((day_info, day_type))

        # For each day number, pick the best entry (one with proper formatting)
        deduplicated_days = []
        for day_number in sorted(day_groups.keys()):
            entries = day_groups[day_number]
            # Prioritize entries that have day name (contain parentheses and day abbreviation)
            best_entry = None
            for entry in entries:
                day_info, day_type = entry
                if "(" in day_info.day and ")" in day_info.day:
                    best_entry = entry
                    break
            if best_entry is None:
                # If no properly formatted entry, take the first one
                best_entry = entries[0]
            deduplicated_days.append(best_entry)

        all_days = deduplicated_days

        lines.append("📅 <b>График по дням:</b>")

        total_work_hours = 0
        work_days_count = 0
        vacation_days_count = 0
        vacation_bs_days_count = 0
        army_days_count = 0
        sick_days_count = 0
        missing_days_count = 0
        days_off_count = 0

        for day_info, day_type in all_days:
            # Check if this is the current day
            day_num = extract_day_number(day_info.day)
            is_current_day = day_num == current_day

            # Format the day with underline if it's current
            day_formatted = (
                f"<u><b>{day_info.day}</b></u>" if is_current_day else day_info.day
            )

            if day_type == "work":
                if day_info.work_hours > 0:
                    lines.append(
                        f"<b>{day_formatted}:</b> <code>{day_info.schedule}</code>"
                    )
                    total_work_hours += day_info.work_hours
                else:
                    lines.append(
                        f"<b>{day_formatted}:</b> <code>{day_info.schedule}</code>"
                    )
                work_days_count += 1
            elif day_type == "day_off":
                lines.append(f"<b>{day_formatted}:</b> Выходной")
                days_off_count += 1
            elif day_type == "vacation":
                lines.append(f"<b>{day_formatted}:</b> ⛱️ Отпуск")
                vacation_days_count += 1
            elif day_type == "vacation_bs":
                lines.append(f"<b>{day_formatted}:</b> ⛱️ БС")
                vacation_bs_days_count += 1
            elif day_type == "army":
                lines.append(f"<b>{day_formatted}:</b> 🎖️ Военкомат")
                army_days_count += 1
            elif day_type == "sick":
                lines.append(f"<b>{day_formatted}:</b> 🤒 Больничный")
                sick_days_count += 1
            elif day_type == "missing":
                lines.append(f"<b>{day_formatted}:</b> 🕵️‍♂️ Отсутствие")
                missing_days_count += 1

        return "\n".join(lines)

    @staticmethod
    def _group_consecutive_schedule(
        work_days: List[DayInfo], current_day: int = None
    ) -> List[str]:
        """Группирует последовательные дни с одинаковым графиком.

        Args:
            work_days: Список рабочих дней
            current_day: Номер текущего дня (для подсветки)

        Returns:
            Список отформатированных строк с группами дней
        """
        if not work_days:
            return []

        schedule_groups = {}
        for day_info in work_days:
            schedule = day_info.schedule
            if schedule not in schedule_groups:
                schedule_groups[schedule] = []
            day_num = day_info.day.split()[0]
            schedule_groups[schedule].append(day_num)

        result = []
        for schedule, days in schedule_groups.items():
            if len(days) == 1:
                day_str = days[0]
                # Check if this is the current day
                try:
                    if current_day and int(day_str) == current_day:
                        result.append(
                            f"<u><b>{day_str}</b></u> → <code>{schedule}</code>"
                        )
                    else:
                        result.append(f"{day_str} → <code>{schedule}</code>")
                except ValueError:
                    result.append(f"{day_str} → <code>{schedule}</code>")
            else:
                days_range = ScheduleFormatter._format_consecutive_days(
                    days, current_day
                )
                result.append(f"{days_range} → <code>{schedule}</code>")

        return result

    @staticmethod
    def _get_today_schedule_line(
        current_day: int,
        work_days: List[DayInfo],
        days_off: List[DayInfo],
        vacation_days: List[DayInfo],
        vacation_bs_days: List[DayInfo],
        army_days: List[DayInfo],
        sick_days: List[DayInfo],
        missing_days: List[DayInfo],
        duty_info: Optional[str] = None,
    ) -> Optional[str]:
        """Get today's schedule line with emoji (optionally with duty and exchange info)."""
        # Check work days
        for day_info in work_days:
            if extract_day_number(day_info.day) == current_day:
                duty_text = f" ({duty_info})" if duty_info else ""
                return f"<blockquote>📍 <b>Сегодня:</b> <code>{day_info.schedule}</code>{duty_text}</blockquote>"

        # Check days off
        for day_info in days_off:
            if extract_day_number(day_info.day) == current_day:
                day_text = "🏠 Выходной"
                if duty_info:
                    day_text += f" ({duty_info})"
                return f"<blockquote>📍 <b>Сегодня:</b> {day_text}</blockquote>"

        # Check vacation
        for day_info in vacation_days:
            if extract_day_number(day_info.day) == current_day:
                return "<blockquote>📍 <b>Сегодня:</b> 🏖 Отпуск</blockquote>"

        # Check vacation BS
        for day_info in vacation_bs_days:
            if extract_day_number(day_info.day) == current_day:
                return "<blockquote>📍 <b>Сегодня:</b> 🏖 БС</blockquote>"

        # Check army
        for day_info in army_days:
            if extract_day_number(day_info.day) == current_day:
                return "<blockquote>📍 <b>Сегодня:</b> 🎖️ Военкомат</blockquote>"

        # Check sick days
        for day_info in sick_days:
            if extract_day_number(day_info.day) == current_day:
                return "<blockquote>📍 <b>Сегодня:</b> 🏥 Больничный</blockquote>"

        # Check missing days
        for day_info in missing_days:
            if extract_day_number(day_info.day) == current_day:
                return "<blockquote>📍 <b>Сегодня:</b> 🕵️‍♂️ Отсутствие</blockquote>"

        return None

    @staticmethod
    def _get_today_schedule_line_with_duties(
        current_day: int,
        schedule_data_with_duties: Dict[str, Tuple[str, Optional[str]]],
        work_days: List[DayInfo],
        days_off: List[DayInfo],
        vacation_days: List[DayInfo],
        vacation_bs_days: List[DayInfo],
        army_days: List[DayInfo],
        sick_days: List[DayInfo],
        missing_days: List[DayInfo],
    ) -> Optional[str]:
        """Get today's schedule line with emoji and duty/exchange info (wrapper for unified method)."""
        # Find today's duty and exchange info
        duty_info = None
        for day_key, (schedule, duty) in schedule_data_with_duties.items():
            if extract_day_number(day_key) == current_day:
                duty_info = duty
                break

        # Use the unified method
        return ScheduleFormatter._get_today_schedule_line(
            current_day,
            work_days,
            days_off,
            vacation_days,
            vacation_bs_days,
            army_days,
            sick_days,
            missing_days,
            duty_info,
        )

    @staticmethod
    def _format_consecutive_days(days: List[str], current_day: int = None) -> str:
        """Format consecutive days"""
        if not days:
            return ""

        try:
            sorted_days = sorted([int(d) for d in days])
        except ValueError:
            return ", ".join(days)

        ranges = []
        start = sorted_days[0]
        end = start

        for day in sorted_days[1:]:
            if day == end + 1:
                end = day
            else:
                # Check if current day is in this range
                if current_day and start <= current_day <= end:
                    if start == end:
                        ranges.append(f"<u><b>{start}</b></u>")
                    else:
                        ranges.append(
                            f"{start}-{end}"
                            if current_day not in (start, end)
                            else f"<u><b>{start}</b></u>-{end}"
                            if current_day == start
                            else f"{start}-<u><b>{end}</b></u>"
                        )
                else:
                    ranges.append(str(start) if start == end else f"{start}-{end}")
                start = end = day

        # Handle the last range
        if current_day and start <= current_day <= end:
            if start == end:
                ranges.append(f"<u><b>{start}</b></u>")
            else:
                ranges.append(
                    f"{start}-{end}"
                    if current_day not in (start, end)
                    else f"<u><b>{start}</b></u>-{end}"
                    if current_day == start
                    else f"{start}-<u><b>{end}</b></u>"
                )
        else:
            ranges.append(str(start) if start == end else f"{start}-{end}")
        return ", ".join(ranges)

    @staticmethod
    def _format_day_range(days: List[str], current_day: int = None) -> str:
        """Format day range"""
        if not days:
            return ""

        day_numbers = []
        for day in days:
            day_num = str(day).split()[0]
            try:
                day_numbers.append(int(day_num))
            except ValueError:
                continue

        if not day_numbers:
            return ", ".join([str(d).split()[0] for d in days])

        return ScheduleFormatter._format_consecutive_days(
            [str(d) for d in day_numbers], current_day
        )

    @staticmethod
    def format_detailed_with_duties(
        month: str,
        schedule_data_with_duties: Dict[str, Tuple[str, Optional[str]]],
        work_days: List[DayInfo],
        days_off: List[DayInfo],
        vacation_days: List[DayInfo],
        vacation_bs_days: List[DayInfo],
        army_days: List[DayInfo],
        sick_days: List[DayInfo],
        missing_days: List[DayInfo],
    ) -> str:
        """Detailed files_processing format with duty and exchange information"""
        lines = [f"<b>👔 Мой график • {month.capitalize()}</b>"]

        # Check if we're viewing the current month
        viewing_current_month = is_current_month(month)
        current_day = get_current_day()

        # Add today's schedule line if viewing current month
        if viewing_current_month:
            today_line = ScheduleFormatter._get_today_schedule_line_with_duties(
                current_day,
                schedule_data_with_duties,
                work_days,
                days_off,
                vacation_days,
                vacation_bs_days,
                army_days,
                sick_days,
                missing_days,
            )
            if today_line:
                lines.append("")
                lines.append(today_line)

        lines.append("")

        all_days = []
        for day_info in work_days:
            all_days.append((day_info, "work"))
        for day_info in days_off:
            all_days.append((day_info, "day_off"))
        for day_info in vacation_days:
            all_days.append((day_info, "vacation"))
        for day_info in vacation_bs_days:
            all_days.append((day_info, "vacation_bs"))
        for day_info in army_days:
            all_days.append((day_info, "army"))
        for day_info in sick_days:
            all_days.append((day_info, "sick"))
        for day_info in missing_days:
            all_days.append((day_info, "missing"))

        all_days.sort(key=lambda x: extract_day_number(x[0].day))

        # Remove duplicates - prioritize entries with proper day formatting
        day_groups = {}
        for day_info, day_type in all_days:
            day_number = extract_day_number(day_info.day)
            if day_number > 0:  # Only process valid day numbers
                if day_number not in day_groups:
                    day_groups[day_number] = []
                day_groups[day_number].append((day_info, day_type))

        # For each day number, pick the best entry (one with proper formatting)
        deduplicated_days = []
        for day_number in sorted(day_groups.keys()):
            entries = day_groups[day_number]
            # Prioritize entries that have day name (contain parentheses and day abbreviation)
            best_entry = None
            for entry in entries:
                day_info, day_type = entry
                if "(" in day_info.day and ")" in day_info.day:
                    best_entry = entry
                    break
            if best_entry is None:
                # If no properly formatted entry, take the first one
                best_entry = entries[0]
            deduplicated_days.append(best_entry)

        all_days = deduplicated_days

        lines.append("📅 <b>График по дням:</b>")

        total_work_hours = 0
        work_days_count = 0
        vacation_days_count = 0
        vacation_bs_days_count = 0
        army_days_count = 0
        sick_days_count = 0
        missing_days_count = 0
        days_off_count = 0

        for day_info, day_type in all_days:
            # Check if this is the current day (only if viewing current month)
            day_num = extract_day_number(day_info.day)
            is_current_day_flag = viewing_current_month and day_num == current_day

            # Get duty and exchange information for this day
            duty_info = None
            day_key = day_info.day
            if day_key in schedule_data_with_duties:
                _, duty_info = schedule_data_with_duties[day_key]

            # Build the full line content first
            if day_type == "work":
                schedule_text = day_info.schedule
                duty_text = f" ({duty_info})" if duty_info else ""
                if is_current_day_flag:
                    line_content = f"<blockquote>{day_info.day}: {schedule_text}{duty_text}</blockquote>"
                else:
                    line_content = (
                        f"{day_info.day}: <code>{schedule_text}</code>{duty_text}"
                    )
                if day_info.work_hours > 0:
                    total_work_hours += day_info.work_hours
                work_days_count += 1
            elif day_type == "day_off":
                day_text = "Выходной"
                if duty_info:
                    day_text += f" ({duty_info})"
                if is_current_day_flag:
                    line_content = f"<u>{day_info.day}: {day_text}</u>"
                else:
                    line_content = f"{day_info.day}: {day_text}"
                days_off_count += 1
            elif day_type == "vacation":
                if is_current_day_flag:
                    line_content = f"<u>{day_info.day}: ⛱️ Отпуск</u>"
                else:
                    line_content = f"{day_info.day}: ⛱️ Отпуск"
                vacation_days_count += 1
            elif day_type == "vacation_bs":
                if is_current_day_flag:
                    line_content = f"<u>{day_info.day}: ⛱️ БС</u>"
                else:
                    line_content = f"{day_info.day}: ⛱️ БС"
                vacation_bs_days_count += 1
            elif day_type == "army":
                if is_current_day_flag:
                    line_content = f"<u>{day_info.day}: 🎖️ Военкомат</u>"
                else:
                    line_content = f"{day_info.day}: 🎖️ Военкомат"
                army_days_count += 1
            elif day_type == "sick":
                if is_current_day_flag:
                    line_content = f"<u>{day_info.day}: 🤒 Больничный</u>"
                else:
                    line_content = f"{day_info.day}: 🤒 Больничный"
                sick_days_count += 1
            elif day_type == "missing":
                if is_current_day_flag:
                    line_content = f"<u>{day_info.day}: 🕵️‍♂️ Отсутствие</u>"
                else:
                    line_content = f"{day_info.day}: 🕵️‍♂️ Отсутствие"
                missing_days_count += 1
            else:
                continue

            # Add the line to the result
            lines.append(line_content)

        return "\n".join(lines)

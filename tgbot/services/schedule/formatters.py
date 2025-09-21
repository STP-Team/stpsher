"""
Schedule formatting functionality.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .models import DayInfo


class ScheduleFormatter:
    """Formatter for schedules"""

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
    ) -> str:
        """Compact schedule format"""
        lines = [f"<b>👔 Мой график • {month.capitalize()}</b>\n"]

        # Get current day and month
        now = datetime.now()
        current_day = now.day
        current_month = now.strftime("%B").lower()

        # Convert month names
        month_names = {
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

        # Check if we're viewing the current month
        is_current_month = month.lower() == month_names.get(
            current_month, current_month
        )
        effective_current_day = current_day if is_current_month else None

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
                days_str = ", ".join(
                    [
                        f"<u><b>{d.day.split()[0]}</b></u>"
                        if effective_current_day
                        and int(d.day.split()[0]) == effective_current_day
                        else d.day.split()[0]
                        for d in days_off
                    ]
                )
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
        """Detailed schedule format"""
        lines = [f"<b>👔 Мой график • {month.capitalize()}</b>\n"]

        # Get current day
        current_day = datetime.now().day

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

        def extract_day_number(day_str: str) -> int:
            try:
                return int(day_str.split()[0])
            except (ValueError, IndexError):
                return 0

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

        lines.append("")
        lines.append("<blockquote expandable>📊 <b>Статистика:</b>")
        lines.append(f"Рабочих дней: <b>{work_days_count}</b>")
        if total_work_hours > 0:
            lines.append(f"Рабочих часов: <b>{round(total_work_hours)}ч</b>")
        lines.append(f"Выходных: <b>{days_off_count}</b>")
        if vacation_days_count > 0:
            lines.append(f"Отпуск: <b>{vacation_days_count} дн.</b>")
        if vacation_bs_days_count > 0:
            lines.append(f"БС: <b>{vacation_days_count} дн.</b>")
        if army_days_count > 0:
            lines.append(f"Военкомат: <b>{vacation_days_count} дн.</b>")
        if sick_days_count > 0:
            lines.append(f"БЛ: <b>{sick_days_count} дн.</b>")
        if missing_days_count > 0:
            lines.append(f"Отсутствий: <b>{missing_days_count} дн.</b>")
        lines.append("</blockquote>")

        return "\n".join(lines)

    @staticmethod
    def _group_consecutive_schedule(
        work_days: List[DayInfo], current_day: int = None
    ) -> List[str]:
        """Group consecutive days with same schedule"""
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
    def get_gender_emoji(name: str) -> str:
        """
        Определение пола по имени
        :param name: Полные ФИО или отчество
        :return: Эмодзи с отображением пола
        """
        parts = name.split()
        if len(parts) >= 3:
            patronymic = parts[2]
            if patronymic.endswith("на"):
                return "👩‍💼"
            elif patronymic.endswith(("ич", "ович", "евич")):
                return "👨‍💼"
        return "👨‍💼"

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
        """Detailed schedule format with duty information"""
        lines = [f"<b>👔 Мой график • {month.capitalize()}</b>\n"]

        # Get current day and month
        now = datetime.now()
        current_day = now.day
        current_month = now.strftime("%B").lower()

        # Convert month names
        month_names = {
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

        # Check if we're viewing the current month
        is_current_month = month.lower() == month_names.get(
            current_month, current_month
        )

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

        def extract_day_number(day_str: str) -> int:
            try:
                return int(day_str.split()[0])
            except (ValueError, IndexError):
                return 0

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
            is_current_day = is_current_month and day_num == current_day

            # Get duty information for this day
            duty_info = None
            day_key = day_info.day
            if day_key in schedule_data_with_duties:
                _, duty_info = schedule_data_with_duties[day_key]

            # Build the full line content first
            if day_type == "work":
                schedule_text = day_info.schedule
                if duty_info:
                    schedule_text += f" ({duty_info})"
                if is_current_day:
                    line_content = f"<u>{day_info.day}: {schedule_text}</u>"
                else:
                    line_content = f"{day_info.day}: <code>{schedule_text}</code>"
                if day_info.work_hours > 0:
                    total_work_hours += day_info.work_hours
                work_days_count += 1
            elif day_type == "day_off":
                day_text = "Выходной"
                if duty_info:
                    day_text += f" ({duty_info})"
                if is_current_day:
                    line_content = f"<u>{day_info.day}: {day_text}</u>"
                else:
                    line_content = f"{day_info.day}: {day_text}"
                days_off_count += 1
            elif day_type == "vacation":
                if is_current_day:
                    line_content = f"<u>{day_info.day}: ⛱️ Отпуск</u>"
                else:
                    line_content = f"{day_info.day}: ⛱️ Отпуск"
                vacation_days_count += 1
            elif day_type == "vacation_bs":
                if is_current_day:
                    line_content = f"<u>{day_info.day}: ⛱️ БС</u>"
                else:
                    line_content = f"{day_info.day}: ⛱️ БС"
                vacation_bs_days_count += 1
            elif day_type == "army":
                if is_current_day:
                    line_content = f"<u>{day_info.day}: 🎖️ Военкомат</u>"
                else:
                    line_content = f"{day_info.day}: 🎖️ Военкомат"
                army_days_count += 1
            elif day_type == "sick":
                if is_current_day:
                    line_content = f"<u>{day_info.day}: 🤒 Больничный</u>"
                else:
                    line_content = f"{day_info.day}: 🤒 Больничный"
                sick_days_count += 1
            elif day_type == "missing":
                if is_current_day:
                    line_content = f"<u>{day_info.day}: 🕵️‍♂️ Отсутствие</u>"
                else:
                    line_content = f"{day_info.day}: 🕵️‍♂️ Отсутствие"
                missing_days_count += 1
            else:
                continue

            # Add the line to the result
            lines.append(line_content)

        lines.append("")
        lines.append("<blockquote expandable>📊 <b>Статистика:</b>")
        lines.append(f"Рабочих дней: <b>{work_days_count}</b>")
        if total_work_hours > 0:
            lines.append(f"Рабочих часов: <b>{round(total_work_hours)}ч</b>")
        lines.append(f"Выходных: <b>{days_off_count}</b>")
        if vacation_days_count > 0:
            lines.append(f"Отпуск: <b>{vacation_days_count} дн.</b>")
        if vacation_bs_days_count > 0:
            lines.append(f"БС: <b>{vacation_bs_days_count} дн.</b>")
        if army_days_count > 0:
            lines.append(f"Военкомат: <b>{army_days_count} дн.</b>")
        if sick_days_count > 0:
            lines.append(f"БЛ: <b>{sick_days_count} дн.</b>")
        if missing_days_count > 0:
            lines.append(f"Отсутствий: <b>{missing_days_count} дн.</b>")
        lines.append("</blockquote>")

        return "\n".join(lines)

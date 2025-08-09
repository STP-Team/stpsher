"""
Schedule formatting functionality.
"""

from typing import List

from .models import DayInfo


class ScheduleFormatter:
    """Formatter for schedules"""

    @staticmethod
    def format_compact(
        month: str,
        work_days: List[DayInfo],
        days_off: List[DayInfo],
        vacation_days: List[DayInfo],
        sick_days: List[DayInfo],
        missing_days: List[DayInfo],
    ) -> str:
        """Compact schedule format"""
        lines = [f"<b>👔 Мой график • {month.capitalize()}</b>\n"]

        if work_days:
            lines.append("🔸 <b>Рабочие:</b>")
            grouped_schedule = ScheduleFormatter._group_consecutive_schedule(work_days)
            lines.extend(grouped_schedule)

        if vacation_days:
            vacation_range = ScheduleFormatter._format_day_range(
                [d.day for d in vacation_days]
            )
            lines.append(f"\n🏖 <b>Отпуск:</b> {vacation_range}")

        if sick_days:
            sick_range = ScheduleFormatter._format_day_range([d.day for d in sick_days])
            lines.append(f"\n🏥 <b>БЛ:</b> {sick_range}")

        if missing_days:
            missing_range = ScheduleFormatter._format_day_range(
                [d.day for d in missing_days]
            )
            lines.append(f"\n🕵️‍♂️ <b>Отсутствия:</b> {missing_range}")

        if days_off:
            if len(days_off) <= 3:
                days_str = ", ".join([d.day.split()[0] for d in days_off])
                lines.append(f"\n🏠 <b>Выходные:</b>\n{days_str}")
            else:
                off_range = ScheduleFormatter._format_day_range(
                    [d.day for d in days_off]
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
        sick_days: List[DayInfo],
        missing_days: List[DayInfo],
    ) -> str:
        """Detailed schedule format"""
        lines = [f"<b>👔 Мой график • {month.capitalize()}</b>\n"]

        all_days = []
        for day_info in work_days:
            all_days.append((day_info, "work"))
        for day_info in days_off:
            all_days.append((day_info, "day_off"))
        for day_info in vacation_days:
            all_days.append((day_info, "vacation"))
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

        lines.append("📅 <b>Расписание по дням:</b>")

        total_work_hours = 0
        work_days_count = 0
        vacation_days_count = 0
        sick_days_count = 0
        missing_days_count = 0
        days_off_count = 0

        for day_info, day_type in all_days:
            if day_type == "work":
                if day_info.work_hours > 0:
                    lines.append(
                        f"<b>{day_info.day}:</b> <code>{day_info.schedule}</code> ({round(day_info.work_hours)}ч)"
                    )
                    total_work_hours += day_info.work_hours
                else:
                    lines.append(
                        f"<b>{day_info.day}:</b> <code>{day_info.schedule}</code>"
                    )
                work_days_count += 1
            elif day_type == "day_off":
                lines.append(f"<b>{day_info.day}:</b> Выходной")
                days_off_count += 1
            elif day_type == "vacation":
                lines.append(f"<b>{day_info.day}:</b> ⛱️ Отпуск")
                vacation_days_count += 1
            elif day_type == "sick":
                lines.append(f"<b>{day_info.day}:</b> 🤒 Больничный")
                sick_days_count += 1
            elif day_type == "missing":
                lines.append(f"<b>{day_info.day}:</b> 🕵️‍♂️ Отсутствие")
                missing_days_count += 1

        lines.append("")
        lines.append("<blockquote expandable>📊 <b>Статистика:</b>")
        lines.append(f"Рабочих дней: <b>{work_days_count}</b>")
        if total_work_hours > 0:
            lines.append(f"Рабочих часов: <b>{round(total_work_hours)}ч</b>")
        lines.append(f"Выходных: <b>{days_off_count}</b>")
        if vacation_days_count > 0:
            lines.append(f"Отпуск: <b>{vacation_days_count} дн.</b>")
        if sick_days_count > 0:
            lines.append(f"БЛ: <b>{sick_days_count} дн.</b>")
        if missing_days_count > 0:
            lines.append(f"Отсутствий: <b>{missing_days_count} дн.</b>")
        lines.append("</blockquote>")

        return "\n".join(lines)

    @staticmethod
    def _group_consecutive_schedule(work_days: List[DayInfo]) -> List[str]:
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
                result.append(f"{days[0]} → <code>{schedule}</code>")
            else:
                days_range = ScheduleFormatter._format_consecutive_days(days)
                result.append(f"{days_range} → <code>{schedule}</code>")

        return result

    @staticmethod
    def _format_consecutive_days(days: List[str]) -> str:
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
                ranges.append(str(start) if start == end else f"{start}-{end}")
                start = end = day

        ranges.append(str(start) if start == end else f"{start}-{end}")
        return ", ".join(ranges)

    @staticmethod
    def _format_day_range(days: List[str]) -> str:
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

        return ScheduleFormatter._format_consecutive_days([str(d) for d in day_numbers])

"""
Head schedule parser functionality.
"""

import logging
import re
from datetime import datetime
from typing import List, Optional

import pandas as pd
import pytz

from .excel_parser import ExcelParser
from .managers import ScheduleFileManager
from .models import HeadInfo, ScheduleType
from .duty_parser import DutyScheduleParser

logger = logging.getLogger(__name__)


class HeadScheduleParser:
    """Parser for head schedules"""

    def __init__(self, uploads_folder: str = "uploads"):
        self.file_manager = ScheduleFileManager(uploads_folder)
        self.excel_parser = ExcelParser(self.file_manager)
        self.yekaterinburg_tz = pytz.timezone("Asia/Yekaterinburg")

    def get_current_yekaterinburg_date(self) -> datetime:
        """Get current date in Yekaterinburg timezone"""
        return datetime.now(self.yekaterinburg_tz)

    def find_date_column(
        self, df: pd.DataFrame, target_date: datetime
    ) -> Optional[int]:
        """Find column with specified date"""
        target_day = target_date.day

        for row_idx in range(min(5, len(df))):
            for col_idx in range(len(df.columns)):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )

                day_pattern = r"^(\d{1,2})[А-Яа-я]{1,2}$"
                match = re.search(day_pattern, cell_value.strip())

                if match and int(match.group(1)) == target_day:
                    logger.debug(f"Found date column {target_day}: {col_idx}")
                    return col_idx

        logger.warning(f"Column for date {target_day} not found")
        return None

    def get_heads_for_date(self, date: datetime, division: str) -> List[HeadInfo]:
        """Get list of group heads for specified date"""
        try:
            schedule_file = self.file_manager.find_schedule_file(
                division, ScheduleType.REGULAR
            )
            if not schedule_file:
                raise FileNotFoundError(f"Schedule file {division} not found")

            df = pd.read_excel(schedule_file, sheet_name="ГРАФИК", header=None)

            date_col = self.find_date_column(df, date)
            if date_col is None:
                logger.warning(f"Date {date.day} not found in schedule")
                return []

            heads = []

            for row_idx in range(len(df)):
                position_found = False
                name = ""

                for col_idx in range(min(10, len(df.columns))):
                    cell_value = (
                        str(df.iloc[row_idx, col_idx])
                        if pd.notna(df.iloc[row_idx, col_idx])
                        else ""
                    )

                    if "Руководитель группы" in cell_value:
                        position_found = True

                    if (
                        not name
                        and len(cell_value.split()) >= 3
                        and re.search(r"[А-Яа-я]", cell_value)
                        and "Руководитель" not in cell_value
                    ):
                        name = cell_value.strip()

                if not position_found or not name:
                    continue

                if date_col < len(df.columns):
                    schedule_cell = (
                        str(df.iloc[row_idx, date_col])
                        if pd.notna(df.iloc[row_idx, date_col])
                        else ""
                    )

                    if schedule_cell and schedule_cell.strip() not in [
                        "",
                        "nan",
                        "None",
                    ]:
                        if re.search(r"\d{1,2}:\d{2}-\d{1,2}:\d{2}", schedule_cell):
                            duty_info = self._check_duty_for_head(name, date, division)

                            heads.append(
                                HeadInfo(
                                    name=name,
                                    schedule=schedule_cell.strip(),
                                    duty_info=duty_info,
                                )
                            )

            logger.info(
                f"Found {len(heads)} group heads on {date.strftime('%d.%m.%Y')}"
            )
            return heads

        except Exception as e:
            logger.error(f"Error getting group heads: {e}")
            return []

    def _check_duty_for_head(
        self, head_name: str, date: datetime, division: str
    ) -> Optional[str]:
        """Check if head has duty on specified date"""
        try:
            duty_parser = DutyScheduleParser()
            duties = duty_parser.get_duties_for_date(date, division)

            for duty in duties:
                if self._names_match(head_name, duty.name):
                    return f"{duty.schedule} [{duty.shift_type}]"

            return None

        except Exception as e:
            logger.debug(f"Error checking duty for {head_name}: {e}")
            return None

    def _names_match(self, name1: str, name2: str) -> bool:
        """Check if names match (considering writing differences)"""
        parts1 = name1.split()
        parts2 = name2.split()

        if len(parts1) >= 2 and len(parts2) >= 2:
            return parts1[0] == parts2[0] and parts1[1] == parts2[1]

        return False

    def get_gender_emoji(self, name: str) -> str:
        """Determine gender by name (simple heuristic)"""
        parts = name.split()
        if len(parts) >= 3:
            patronymic = parts[2]
            if patronymic.endswith("на"):
                return "👩‍💼"
            elif patronymic.endswith(("ич", "ович", "евич")):
                return "👨‍💼"
        return "👨‍💼"

    def format_heads_for_date(self, date: datetime, heads: List[HeadInfo]) -> str:
        """Format heads list for display"""
        if not heads:
            return f"<b>👑 Руководители групп • {date.strftime('%d.%m.%Y')}</b>\n\n❌ Руководители групп на эту дату не найдены"

        lines = [f"<b>👑 Руководители групп • {date.strftime('%d.%m.%Y')}</b>\n"]

        time_groups = {}
        for head in heads:
            time_schedule = head.schedule
            if not time_schedule or not re.search(
                r"\d{1,2}:\d{2}-\d{1,2}:\d{2}", time_schedule
            ):
                continue

            time_match = re.search(r"(\d{1,2}:\d{2}-\d{1,2}:\d{2})", time_schedule)
            time_key = time_match.group(1) if time_match else time_schedule

            if time_key not in time_groups:
                time_groups[time_key] = []
            time_groups[time_key].append(head)

        def parse_time_start(time_str: str) -> int:
            try:
                if "-" in time_str:
                    start_time = time_str.split("-")[0].strip()
                    hour, minute = start_time.split(":")
                    return int(hour) * 60 + int(minute)
                return 0
            except (ValueError, IndexError):
                return 0

        sorted_times = sorted(time_groups.keys(), key=parse_time_start)

        for time_schedule in sorted_times:
            group_heads = time_groups[time_schedule]

            lines.append(f"⏰ <b>{time_schedule}</b>")

            for head in group_heads:
                gender_emoji = self.get_gender_emoji(head.name)
                head_line = f"{gender_emoji} {head.name}"

                if head.duty_info:
                    head_line += f" ({head.duty_info})"

                lines.append(head_line)

            lines.append("")

        if lines and lines[-1] == "":
            lines.pop()

        return "\n".join(lines)

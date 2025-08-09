"""
Main schedule parsers.
"""

import logging
from typing import Dict

import pandas as pd

from .analyzers import ScheduleAnalyzer
from .excel_parser import ExcelParser
from .formatters import ScheduleFormatter
from .managers import ScheduleFileManager
from .models import ScheduleType

logger = logging.getLogger(__name__)


class ScheduleParser:
    """Main schedule parser class"""

    def __init__(self, uploads_folder: str = "uploads"):
        self.file_manager = ScheduleFileManager(uploads_folder)
        self.excel_parser = ExcelParser(self.file_manager)
        self.analyzer = ScheduleAnalyzer()
        self.formatter = ScheduleFormatter()

    def get_user_schedule(
        self,
        fullname: str,
        month: str,
        division: str,
        schedule_type: ScheduleType = ScheduleType.REGULAR,
    ) -> Dict[str, str]:
        """Get user schedule"""
        try:
            schedule_file = self.file_manager.find_schedule_file(
                division, schedule_type
            )
            if not schedule_file:
                raise FileNotFoundError(f"Schedule file {division} not found")

            df = self.excel_parser.read_excel_file(schedule_file, schedule_type)
            start_col, end_col = self.excel_parser.find_month_columns(df, month)
            day_headers = self.excel_parser.find_day_headers(df, start_col, end_col)

            user_row_idx = self.excel_parser.find_user_row(df, fullname)
            if user_row_idx is None:
                raise ValueError(f"User {fullname} not found in schedule")

            schedule = {}
            for col_idx in range(start_col, end_col + 1):
                if col_idx in day_headers:
                    day = day_headers[col_idx]
                    schedule_value = (
                        str(df.iloc[user_row_idx, col_idx])
                        if pd.notna(df.iloc[user_row_idx, col_idx])
                        else ""
                    )

                    schedule_value = schedule_value.strip()
                    if schedule_value.lower() in ["nan", "none", ""]:
                        schedule_value = "Не указано"

                    schedule[day] = schedule_value

            logger.info(
                f"Got schedule for '{fullname}' for {month}: {len(schedule)} days"
            )
            return schedule

        except Exception as e:
            logger.error(f"Error getting schedule: {e}")
            raise

    def get_user_schedule_formatted(
        self,
        fullname: str,
        month: str,
        division: str,
        compact: bool = False,
        schedule_type: ScheduleType = ScheduleType.REGULAR,
    ) -> str:
        """Get formatted user schedule"""
        try:
            schedule_data = self.get_user_schedule(
                fullname, month, division, schedule_type
            )

            if not schedule_data:
                return f"❌ Schedule for <b>{fullname}</b> for {month} not found"

            work_days, days_off, vacation_days, sick_days, missing_days = (
                self.analyzer.analyze_schedule(schedule_data)
            )

            if compact:
                return self.formatter.format_compact(
                    month, work_days, days_off, vacation_days, sick_days, missing_days
                )
            else:
                return self.formatter.format_detailed(
                    month, work_days, days_off, vacation_days, sick_days, missing_days
                )

        except Exception as e:
            logger.error(f"Error formatting schedule: {e}")
            return f"❌ <b>Error getting schedule:</b>\n<code>{e}</code>"

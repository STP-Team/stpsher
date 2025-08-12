"""
Excel file parsing functionality.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
from pandas import DataFrame

from .managers import ScheduleFileManager, MonthManager

logger = logging.getLogger(__name__)


class ExcelParser:
    """Parser for Excel files"""

    def __init__(self, file_manager: ScheduleFileManager):
        self.file_manager = file_manager

    def read_excel_file(self, file_path: Path) -> DataFrame | None:
        """Read Excel file with various sheet handling"""
        sheet_name = "ГРАФИК"

        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            logger.debug(f"Successfully read sheet: {sheet_name}")
            return df
        except Exception as e:
            logger.debug(f"Failed to read sheet '{sheet_name}': {e}")

    def find_month_columns(self, df: pd.DataFrame, month: str) -> Tuple[int, int]:
        """Find columns for specified month"""
        month = MonthManager.normalize_month(month)

        month_start_col = self._find_month_start(df, month)
        if month_start_col is None:
            raise ValueError(f"Month '{month}' not found in file")

        month_end_col = self._find_month_end(df, month, month_start_col)

        logger.debug(
            f"Month '{month}' found in columns {month_start_col}-{month_end_col}"
        )
        return month_start_col, month_end_col

    def _find_month_start(self, df: pd.DataFrame, month: str) -> Optional[int]:
        """Find starting column of month"""
        # Search in column headers
        for col_idx, col in enumerate(df.columns):
            if isinstance(col, str) and month in col.upper():
                return col_idx

        # Search in first rows
        for row_idx in range(min(5, len(df))):
            for col_idx, cell_value in enumerate(df.iloc[row_idx]):
                if isinstance(cell_value, str) and month in cell_value.upper():
                    return col_idx

        return None

    def _find_month_end(
        self, df: pd.DataFrame, current_month: str, start_col: int
    ) -> int:
        """Find ending column of month"""
        month_end_col = len(df.columns) - 1

        for col_idx in range(start_col + 1, len(df.columns)):
            col_name = (
                str(df.columns[col_idx]) if df.columns[col_idx] is not None else ""
            )

            for month in MonthManager.MONTHS_ORDER:
                if month != current_month and month in col_name.upper():
                    return col_idx - 1

            for row_idx in range(min(5, len(df))):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )

                for month in MonthManager.MONTHS_ORDER:
                    if month != current_month and month in cell_value.upper():
                        return col_idx - 1

        return month_end_col

    def find_day_headers(
        self, df: pd.DataFrame, start_col: int, end_col: int
    ) -> Dict[int, str]:
        """Find day headers"""
        day_headers = {}

        for row_idx in range(min(5, len(df))):
            for col_idx in range(start_col, end_col + 1):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )

                day_pattern = r"(\d{1,2})([А-Яа-я]{1,2})"
                match = re.search(day_pattern, cell_value)

                if match:
                    day_num = match.group(1)
                    day_name = match.group(2)
                    day_headers[col_idx] = f"{day_num} ({day_name})"
                elif (
                    cell_value.strip().isdigit() and 1 <= int(cell_value.strip()) <= 31
                ):
                    day_headers[col_idx] = cell_value.strip()

        logger.debug(f"Found {len(day_headers)} days in headers")
        return day_headers

    def find_user_row(self, df: pd.DataFrame, fullname: str) -> Optional[int]:
        """Find user row"""
        for row_idx in range(len(df)):
            for col_idx in range(min(3, len(df.columns))):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )

                if fullname in cell_value:
                    logger.debug(f"User '{fullname}' found in row {row_idx}")
                    return row_idx

        return None

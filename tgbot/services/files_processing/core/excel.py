"""Сервис для чтения Excel файлов."""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from tgbot.misc.dicts import schedule_types

from ..utils.excel_helpers import get_cell_value
from ..utils.validators import is_valid_fullname
from .cache import get_cache
from .constants import MONTHS_ORDER

logger = logging.getLogger(__name__)


class ExcelReader:
    """Основной Reader для файлов Excel."""

    def __init__(self, file_path: Path, sheet_name: str = "ГРАФИК"):
        """Инициализация ExcelReader с указанным файлом и листом.

        Args:
            file_path: Путь к файлу Excel
            sheet_name: Название листа для чтения
        """
        self.file_path = file_path
        self.sheet_name = sheet_name
        self.cache = get_cache()
        self._df: Optional[pd.DataFrame] = None

    @property
    def df(self) -> pd.DataFrame:
        """Получает датафрейм.

        Returns:
            Pandas DataFrame с данными из Excel

        Raises:
            ValueError: Если не удалось загрузить файл
        """
        if self._df is None:
            self._df = self.cache.get_dataframe(self.file_path, self.sheet_name)
            if self._df is None:
                raise ValueError(f"Failed to load {self.file_path}:{self.sheet_name}")
        return self._df

    def get_cell(self, row: int, col: int) -> str:
        """Возвращает значение клетки.

        Args:
            row: Индекс строки
            col: Индекс колонки

        Returns:
            Строковое значение клетки
        """
        try:
            return get_cell_value(self.df, row, col, "")
        except Exception as e:
            logger.debug(
                f"[Excel] Ошибка получения значения клетки ({row}, {col}): {e}"
            )
            return ""

    def find_user_row(self, fullname: str) -> Optional[int]:
        """Поиск строк пользователя с использованием предварительно созданного индекса.

        Args:
            fullname: ФИО пользователя

        Returns:
            Индекс строки или None если ничего не найдено
        """
        # Сначала пробуем индекс (O(1) lookup)
        row_idx = self.cache.get_user_row(self.file_path, fullname)
        if row_idx is not None:
            return row_idx

        # Переход к ручному поиску, если индекс не построен
        for row_idx in range(self.df.shape[0]):
            for col_idx in range(min(3, self.df.shape[1])):
                cell_value = self.get_cell(row_idx, col_idx)
                if fullname in cell_value:
                    logger.debug(f"[Excel] '{fullname}' найден на строке {row_idx}")
                    return row_idx

        logger.debug(f"[Excel] '{fullname}' не найден в файле")
        return None

    def find_date_column(self, date) -> Optional[int]:
        """Поиск столбца даты с использованием предварительно созданного индекса.

        Args:
            date: Объект datetime или кортеж (month: str, day: int)

        Returns:
            Индекс столбца или None если не найдено
        """
        from datetime import datetime

        from .cache import normalize_month

        # Handle datetime object
        if isinstance(date, datetime):
            month_normalized = MONTHS_ORDER[date.month - 1]
            day = date.day
        # Handle tuple of (month, day)
        elif isinstance(date, tuple):
            month_normalized = normalize_month(date[0])
            day = date[1]
        else:
            logger.error(f"Invalid date type: {type(date)}")
            return None

        # Try index first (O(1) lookup)
        col_idx = self.cache.get_date_column(self.file_path, month_normalized, day)
        if col_idx is not None:
            return col_idx

        # Fallback to manual search
        return self._find_date_column_fallback(month_normalized, day)

    def _find_date_column_fallback(self, month: str, day: int) -> Optional[int]:
        """Резервный метод для поиска столбца даты.

        Args:
            month: Название месяца
            day: Номер дня

        Returns:
            Индекс столбца или None если не найдено
        """
        # Find month section first
        month_start_col = None
        for row_idx in range(min(3, self.df.shape[0])):
            for col_idx in range(self.df.shape[1]):
                cell_value = self.get_cell(row_idx, col_idx)
                if month in cell_value.upper():
                    month_start_col = col_idx
                    break
            if month_start_col is not None:
                break

        if month_start_col is None:
            return None

        # Find day within month section
        month_end_col = min(month_start_col + 35, self.df.shape[1])  # ~31 days max
        for row_idx in range(min(5, self.df.shape[0])):
            for col_idx in range(month_start_col, month_end_col):
                cell_value = self.get_cell(row_idx, col_idx)
                if not cell_value:
                    continue

                # Pattern for day with letters like "28Чт"
                day_pattern = r"^(\d{1,2})[А-Яа-я]{0,2}$"
                match = re.search(day_pattern, cell_value.strip())

                if match and int(match.group(1)) == day:
                    logger.debug(f"Found day {day} at column {col_idx}")
                    return col_idx

        return None

    def get_month_range(self, month: str) -> Optional[Tuple[int, int]]:
        """Находит начальный и конечный столбцы для месяца.

        Args:
            month: Название месяца на русском

        Returns:
            Кортеж (start_col, end_col) или None если не найдено
        """
        from .cache import normalize_month

        month = normalize_month(month)

        # Find month start
        start_col = None
        for row_idx in range(min(3, self.df.shape[0])):
            for col_idx in range(self.df.shape[1]):
                cell_value = self.get_cell(row_idx, col_idx)
                if month in cell_value.upper():
                    start_col = col_idx
                    break
            if start_col is not None:
                break

        if start_col is None:
            return None

        # Find month end (start of next month or end of sheet)
        end_col = self.df.shape[1] - 1

        months_order = MONTHS_ORDER

        try:
            current_month_idx = months_order.index(month)
            for next_month in months_order[current_month_idx + 1 :]:
                for row_idx in range(min(3, self.df.shape[0])):
                    for col_idx in range(start_col + 1, self.df.shape[1]):
                        cell_value = self.get_cell(row_idx, col_idx)
                        if next_month in cell_value.upper():
                            end_col = col_idx - 1
                            return start_col, end_col
        except ValueError:
            pass

        return start_col, end_col

    def get_day_headers(self, start_col: int, end_col: int) -> Dict[int, str]:
        """Находит заголовки дней в диапазоне столбцов.

        Args:
            start_col: Начальный индекс столбца
            end_col: Конечный индекс столбца

        Returns:
            Словарь с маппингом индекса столбца на строку дня
        """
        day_headers = {}

        for row_idx in range(min(5, self.df.shape[0])):
            for col_idx in range(start_col, end_col + 1):
                cell_value = self.get_cell(row_idx, col_idx)

                # Pattern for day with letters
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

        return day_headers

    def extract_user_schedule(self, fullname: str, month: str) -> Dict[str, str]:
        """Извлекает полный график для пользователя в указанном месяце.

        Args:
            fullname: ФИО пользователя
            month: Название месяца

        Returns:
            Словарь с маппингом дня на значение графика

        Raises:
            ValueError: Если пользователь или месяц не найден
        """
        # Fast user row lookup
        user_row = self.find_user_row(fullname)
        if user_row is None:
            raise ValueError(f"User {fullname} not found")

        # Get month range
        month_range = self.get_month_range(month)
        if month_range is None:
            raise ValueError(f"Month {month} not found")

        start_col, end_col = month_range
        day_headers = self.get_day_headers(start_col, end_col)

        # Extract schedule values
        schedule = {}
        for col_idx, day in day_headers.items():
            cell_value = self.get_cell(user_row, col_idx)
            schedule_value = cell_value.strip() if cell_value is not None else ""

            if schedule_value.lower() in schedule_types["day_off"]:
                schedule_value = None

            schedule[day] = schedule_value

        return schedule

    def extract_all_users(self) -> List[str]:
        """Извлекает все имена пользователей из файла.

        Returns:
            Список ФИО пользователей
        """
        users = []

        for row_idx in range(self.df.shape[0]):
            for col_idx in range(min(4, self.df.shape[1])):
                cell_value = self.get_cell(row_idx, col_idx)

                if is_valid_fullname(cell_value.strip()):
                    users.append(cell_value.strip())
                    break

        return users

    def batch_get_cells(self, positions: List[Tuple[int, int]]) -> List[str]:
        """Пакетное извлечение нескольких ячеек эффективным способом.

        Args:
            positions: Список кортежей (row, col)

        Returns:
            Список значений ячеек
        """
        return [self.get_cell(row, col) for row, col in positions]

    def get_column(
        self, col_idx: int, start_row: int = 0, end_row: Optional[int] = None
    ) -> List[str]:
        """Получает весь столбец эффективным способом.

        Args:
            col_idx: Индекс столбца
            start_row: Начальная строка (по умолчанию 0)
            end_row: Конечная строка (по умолчанию последняя строка)

        Returns:
            Список значений ячеек
        """
        if end_row is None:
            end_row = self.df.shape[0]

        try:
            from ..utils.excel_helpers import get_column_values

            return get_column_values(self.df, col_idx, start_row, end_row)
        except Exception as e:
            logger.error(f"Error getting column {col_idx}: {e}")
            return []

    def get_row(
        self, row_idx: int, start_col: int = 0, end_col: Optional[int] = None
    ) -> List[str]:
        """Получает всю строку эффективным способом.

        Args:
            row_idx: Индекс строки
            start_col: Начальный столбец (по умолчанию 0)
            end_col: Конечный столбец (по умолчанию последний столбец)

        Returns:
            Список значений ячеек
        """
        try:
            from ..utils.excel_helpers import get_row_values

            return get_row_values(self.df, row_idx, start_col, end_col)
        except Exception as e:
            logger.error(f"Error getting row {row_idx}: {e}")
            return []

    def search_value(
        self, value: str, max_rows: int = 100, max_cols: int = 10
    ) -> List[Tuple[int, int]]:
        """Ищет значение в DataFrame.

        Args:
            value: Значение для поиска
            max_rows: Максимальное количество строк для поиска
            max_cols: Максимальное количество столбцов для поиска

        Returns:
            Список позиций (row, col) где найдено значение
        """
        positions = []

        for row_idx in range(min(max_rows, self.df.shape[0])):
            for col_idx in range(min(max_cols, self.df.shape[1])):
                cell_value = self.get_cell(row_idx, col_idx)
                if value in cell_value:
                    positions.append((row_idx, col_idx))

        return positions

    @property
    def shape(self) -> Tuple[int, int]:
        """Получает размер DataFrame.

        Returns:
            Кортеж (количество строк, количество столбцов)
        """
        return self.df.shape

    def close(self):
        """Очищает внутреннюю ссылку на DataFrame."""
        self._df = None

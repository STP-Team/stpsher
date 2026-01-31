"""Утилиты для парсинга графиков.

Модуль предоставляет общие функции для извлечения данных графиков из Excel файлов,
которые используются различными парсерами и детекторами.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from pandas import DataFrame

from ..core.constants import MONTHS_ORDER
from ..utils.excel_helpers import get_cell_value
from ..utils.validators import is_valid_fullname

logger = logging.getLogger(__name__)


def extract_users_schedules(file_path: Path) -> Dict[str, Dict[str, str]]:
    """Извлекает полные расписания всех сотрудников из Excel файла за один проход.

    Использует ту же логику, что и рабочие парсеры, но для всех месяцев сразу.

    Args:
        file_path: Путь до проверяемого файла графиков

    Returns:
        Словарь с полным расписанием сотрудников за все месяцы
    """
    schedules = {}

    try:
        # Читаем файл графиков
        df = pd.read_excel(file_path, sheet_name=0, header=None, dtype=str)
        logger.debug(f"[График] Прочитан Excel файл {file_path}, размер: {df.shape}")

        # Находим все месяцы и их диапазоны колонок
        months_ranges = find_all_months_ranges(df)
        if not months_ranges:
            logger.warning(f"[График] Месяцы не найдены в файле {file_path}")
            return schedules

        logger.info(f"[График] Найдены месяцы: {list(months_ranges.keys())}")

        # Находим всех пользователей в файле
        users_rows = find_all_users_rows(df)
        if not users_rows:
            logger.warning(f"[График] Пользователи не найдены в файле {file_path}")
            return schedules

        logger.info(f"[График] Найдено пользователей: {len(users_rows)}")

        # Для каждого пользователя извлекаем полное расписание по всем месяцам
        for fullname, row_idx in users_rows.items():
            user_complete_schedule = {}

            # Проходим по всем месяцам
            for month, (start_col, end_col) in months_ranges.items():
                # Находим заголовки дней для этого месяца
                day_headers = find_day_headers_in_range(df, start_col, end_col)

                logger.debug(
                    f"[График] {fullname} - {month}: найдено {len(day_headers)} дней"
                )

                # Извлекаем значения расписания для этого месяца
                for col_idx in range(start_col, end_col + 1):
                    if col_idx in day_headers:
                        day_name = day_headers[col_idx]
                        schedule_key = f"{month}_{day_name}"

                        if col_idx < len(df.columns):
                            schedule_value = get_cell_value(df, row_idx, col_idx)
                            user_complete_schedule[schedule_key] = (
                                schedule_value.strip()
                            )

            schedules[fullname] = user_complete_schedule

        logger.info(
            f"[График] Извлечено полных расписаний: {len(schedules)} пользователей"
        )
        return schedules

    except Exception as e:
        logger.error(f"[График] Ошибка извлечения расписаний из {file_path}: {e}")
        return {}


def find_all_months_ranges(df: DataFrame) -> Dict[str, tuple]:
    """Находит диапазоны колонок для всех месяцев в файле.

    Args:
        df: Датафрейм

    Returns:
        Словарь доступных диапазонов месяцев
    """
    months_ranges = {}
    months_order = MONTHS_ORDER

    def find_month_column(
        target_month: str, target_first_col: int = 0
    ) -> Optional[int]:
        """Находит колонку с указанным месяцем."""
        for col_idx in range(target_first_col, len(df.columns)):
            # Проверяем заголовки колонок
            col_name = str(df.columns[col_idx]).upper() if df.columns[col_idx] else ""
            if target_month in col_name:
                return col_idx

            # Проверяем первые строки
            for row_idx in range(min(5, len(df))):
                val = (
                    df.iat[row_idx, col_idx]
                    if pd.notna(df.iat[row_idx, col_idx])
                    else ""
                )
                if isinstance(val, str) and target_month in val.upper():
                    return col_idx
        return None

    # Находим все месяцы по порядку
    last_end_col = 0
    for month in months_order:
        start_col = find_month_column(month, last_end_col)
        if start_col is not None:
            # Находим конец этого месяца (начало следующего месяца - 1)
            end_col = len(df.columns) - 1  # По умолчанию до конца файла

            # Ищем следующий месяц
            for next_month in months_order[months_order.index(month) + 1 :]:
                next_start = find_month_column(next_month, start_col + 1)
                if next_start is not None:
                    end_col = next_start - 1
                    break

            months_ranges[month] = (start_col, end_col)
            last_end_col = end_col + 1

    return months_ranges


def find_all_users_rows(df: DataFrame) -> Dict[str, int]:
    """Находит строки всех пользователей в файле.

    Args:
        df: Датафрейм

    Returns:
        Словарь со списком пользователей и индекса строк, на которых они находятся
    """
    users_rows = {}

    for row_idx in range(len(df)):
        for col_idx in range(min(4, len(df.columns))):
            cell_value = get_cell_value(df, row_idx, col_idx)

            if is_valid_fullname(cell_value.strip()):
                fullname = cell_value.strip()
                users_rows[fullname] = row_idx
                break

    return users_rows


def find_day_headers_in_range(
    df: DataFrame, start_col: int, end_col: int
) -> Dict[int, str]:
    """Находит заголовки дней в указанном диапазоне колонок.

    Args:
        df: Датафрейм
        start_col: Стартовая колонка
        end_col: Конечная колонка

    Returns:
        Словарь заголовков дней
    """
    day_headers = {}

    for row_idx in range(min(5, len(df))):
        for col_idx in range(start_col, end_col + 1):
            cell_value = get_cell_value(df, row_idx, col_idx)

            # Паттерн: число (1-31) + 1-2 кириллические буквы
            day_with_weekday_pattern = r"^(\d{1,2})([А-Яа-я]{1,2})$"
            match = re.search(day_with_weekday_pattern, cell_value.strip())

            if match:
                day_num = match.group(1)
                day_abbr = match.group(2)

                if 1 <= int(day_num) <= 31:
                    day_headers[col_idx] = f"{day_num}({day_abbr})"
                    logger.debug(
                        f"[График] Найден день: колонка {col_idx} = '{day_num}({day_abbr})' из '{cell_value}'"
                    )
                    continue

    logger.debug(
        f"[График] Найдено {len(day_headers)} дней в диапазоне колонок {start_col}-{end_col}: {list(day_headers.values())}"
    )
    return day_headers


def normalize_schedule_value(value: str) -> str:
    """Нормализует значение расписания для сравнения.

    Args:
        value: Значение графика

    Returns:
        Нормализованное значение
    """
    if not value or value.strip().lower() in ["", "nan", "none", "не указано", "0"]:
        return ""

    return value.strip()


def compare_schedules(
    fullname: str, old_schedule: Dict[str, str], new_schedule: Dict[str, str]
) -> Optional[Dict]:
    """Сравнивает расписания пользователя и возвращает детали изменений.

    Args:
        fullname: Полные ФИО
        old_schedule: Словарь со старым графиком сотрудника
        new_schedule: Словарь с новым графиком сотрудника

    Returns:
        Словарь с данными о днях с измененными графиками
    """
    changes = []

    # Получаем все дни из обоих расписаний
    all_days = set(old_schedule.keys()) | set(new_schedule.keys())

    for day in all_days:
        old_value = normalize_schedule_value(old_schedule.get(day, ""))
        new_value = normalize_schedule_value(new_schedule.get(day, ""))

        if old_value != new_value:
            # Очищаем название дня для отображения
            display_day = day.replace("_", " ").replace("(", " (")

            changes.append({
                "day": display_day,
                "old_value": old_value or "выходной",
                "new_value": new_value or "выходной",
            })

    if changes:
        logger.info(f"[График] Найдены изменения для {fullname}: {len(changes)} дней")
        # ОТЛАДКА: Добавляем детализированный лог изменений
        for change in changes:
            logger.debug(
                f"[График] Изменение для {fullname} - {change['day']}: "
                f"'{change['old_value']}' -> '{change['new_value']}'"
            )
        return {"fullname": fullname, "changes": changes}

    return None


def extract_division_from_filename(filename: str) -> str:
    """Достает направление из названия файла.

    Args:
        filename: Название файла

    Returns:
        Направление, которому принадлежит файл
    """
    filename_upper = filename.upper()

    division_map = {"НЦК": "НЦК", "НТП1": "НТП1", "НТП2": "НТП2"}

    for key, value in division_map.items():
        if key in filename_upper:
            return value

    return "НТП"

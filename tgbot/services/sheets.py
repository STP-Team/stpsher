import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import pandas as pd
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class ScheduleParser:
    """
    Класс для парсинга расписаний из Excel файлов
    """

    def __init__(self, uploads_folder: str = "uploads"):
        self.uploads_folder = Path(uploads_folder)

    def find_schedule_file(self, year: int = None) -> Optional[Path]:
        """
        Ищет файл расписания в папке uploads

        Args:
            year: Год для поиска файла (по умолчанию текущий год)

        Returns:
            Path к найденному файлу или None
        """
        if year is None:
            year = datetime.now().year

        # Паттерны поиска файлов
        patterns = [
            f"ГРАФИК НЦК II {year}*",
            f"график нцк ii {year}*",
            f"ГРАФИК*{year}*",
            f"график*{year}*",
        ]

        for pattern in patterns:
            files = list(self.uploads_folder.glob(pattern))
            if files:
                logger.info(f"Найден файл расписания: {files[0]}")
                return files[0]

        # Если не найден файл с годом, ищем любой файл с "ГРАФИК"
        files = list(self.uploads_folder.glob("ГРАФИК*"))
        if files:
            logger.info(f"Найден файл расписания без года: {files[0]}")
            return files[0]

        logger.error(f"Файл расписания не найден в папке {self.uploads_folder}")
        return None

    def _normalize_month_name(self, month: str) -> str:
        """
        Нормализует название месяца к стандартному виду

        Args:
            month: Название месяца

        Returns:
            Нормализованное название месяца в верхнем регистре
        """
        month_mapping = {
            "январь": "ЯНВАРЬ",
            "jan": "ЯНВАРЬ",
            "january": "ЯНВАРЬ",
            "февраль": "ФЕВРАЛЬ",
            "feb": "ФЕВРАЛЬ",
            "february": "ФЕВРАЛЬ",
            "март": "МАРТ",
            "mar": "МАРТ",
            "march": "МАРТ",
            "апрель": "АПРЕЛЬ",
            "apr": "АПРЕЛЬ",
            "april": "АПРЕЛЬ",
            "май": "МАЙ",
            "may": "МАЙ",
            "июнь": "ИЮНЬ",
            "jun": "ИЮНЬ",
            "june": "ИЮНЬ",
            "июль": "ИЮЛЬ",
            "jul": "ИЮЛЬ",
            "july": "ИЮЛЬ",
            "август": "АВГУСТ",
            "aug": "АВГУСТ",
            "august": "АВГУСТ",
            "сентябрь": "СЕНТЯБРЬ",
            "sep": "СЕНТЯБРЬ",
            "september": "СЕНТЯБРЬ",
            "октябрь": "ОКТЯБРЬ",
            "oct": "ОКТЯБРЬ",
            "october": "ОКТЯБРЬ",
            "ноябрь": "НОЯБРЬ",
            "nov": "НОЯБРЬ",
            "november": "НОЯБРЬ",
            "декабрь": "ДЕКАБРЬ",
            "dec": "ДЕКАБРЬ",
            "december": "ДЕКАБРЬ",
        }

        normalized = month_mapping.get(month.lower(), month.upper())
        return normalized

    def _find_month_columns(self, df: pd.DataFrame, month: str) -> Tuple[int, int]:
        """
        Находит начальную и конечную колонки для указанного месяца

        Args:
            df: DataFrame с данными расписания
            month: Название месяца

        Returns:
            Tuple с индексами начальной и конечной колонки месяца
        """
        month = self._normalize_month_name(month)

        # Ищем колонку с названием месяца
        month_start_col = None
        for col_idx, col in enumerate(df.columns):
            if isinstance(col, str) and month in col.upper():
                month_start_col = col_idx
                break

        if month_start_col is None:
            # Проверяем первые несколько строк на наличие месяца
            for row_idx in range(min(5, len(df))):
                for col_idx, cell_value in enumerate(df.iloc[row_idx]):
                    if isinstance(cell_value, str) and month in cell_value.upper():
                        month_start_col = col_idx
                        break
                if month_start_col is not None:
                    break

        if month_start_col is None:
            raise ValueError(f"Месяц '{month}' не найден в файле")

        # Ищем конец месяца (следующий месяц или конец данных)
        month_end_col = len(df.columns) - 1

        # Список месяцев для поиска следующего
        months = [
            "ЯНВАРЬ",
            "ФЕВРАЛЬ",
            "МАРТ",
            "АПРЕЛЬ",
            "МАЙ",
            "ИЮНЬ",
            "ИЮЛЬ",
            "АВГУСТ",
            "СЕНТЯБРЬ",
            "ОКТЯБРЬ",
            "НОЯБРЬ",
            "ДЕКАБРЬ",
        ]

        for col_idx in range(month_start_col + 1, len(df.columns)):
            col_name = (
                str(df.columns[col_idx]) if df.columns[col_idx] is not None else ""
            )

            # Проверяем название колонки
            for m in months:
                if m != month and m in col_name.upper():
                    month_end_col = col_idx - 1
                    break

            if month_end_col != len(df.columns) - 1:
                break

            # Проверяем содержимое ячеек в первых строках
            for row_idx in range(min(5, len(df))):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )
                for m in months:
                    if m != month and m in cell_value.upper():
                        month_end_col = col_idx - 1
                        break
                if month_end_col != len(df.columns) - 1:
                    break

            if month_end_col != len(df.columns) - 1:
                break

        logger.info(
            f"Найден месяц '{month}' в колонках {month_start_col}-{month_end_col}"
        )
        return month_start_col, month_end_col

    def _find_day_headers(
        self, df: pd.DataFrame, start_col: int, end_col: int
    ) -> Dict[int, str]:
        """
        Находит заголовки дней в указанном диапазоне колонок

        Args:
            df: DataFrame с данными
            start_col: Начальная колонка
            end_col: Конечная колонка

        Returns:
            Словарь {номер_колонки: день}
        """
        day_headers = {}

        # Ищем строки с днями (обычно в первых 5 строках)
        for row_idx in range(min(5, len(df))):
            for col_idx in range(start_col, end_col + 1):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )

                # Ищем паттерны дней: "1Пт", "2Сб", "3Вс" и т.д.

                day_pattern = r"(\d{1,2})([А-Яа-я]{1,2})"
                match = re.search(day_pattern, cell_value)

                if match:
                    day_num = match.group(1)
                    day_name = match.group(2)
                    day_headers[col_idx] = f"{day_num} ({day_name})"
                elif (
                    cell_value.strip().isdigit() and 1 <= int(cell_value.strip()) <= 31
                ):
                    # Простые числа дней
                    day_headers[col_idx] = cell_value.strip()

        logger.info(f"Найдено {len(day_headers)} дней в заголовках")
        return day_headers

    def get_user_schedule(
        self, fullname: str, month: str, year: int = None
    ) -> Dict[str, str]:
        """
        Получает расписание пользователя на указанный месяц

        Args:
            fullname: Полное имя пользователя (ФИО)
            month: Название месяца
            year: Год (по умолчанию текущий)

        Returns:
            Словарь {день: расписание}
        """
        try:
            # Находим файл расписания
            schedule_file = self.find_schedule_file(year)
            if not schedule_file:
                raise FileNotFoundError("Файл расписания не найден")

            # Читаем Excel файл
            logger.info(f"Читаем файл: {schedule_file}")

            # Пробуем разные листы
            sheet_names = ["ГРАФИК", "График", "график", "Sheet1", 0]
            df = None

            for sheet_name in sheet_names:
                try:
                    df = pd.read_excel(
                        schedule_file, sheet_name=sheet_name, header=None
                    )
                    logger.info(f"Успешно прочитан лист: {sheet_name}")
                    break
                except Exception as e:
                    logger.debug(f"Не удалось прочитать лист '{sheet_name}': {e}")
                    continue

            if df is None:
                raise ValueError("Не удалось прочитать ни один лист из файла")

            # Находим колонки месяца
            start_col, end_col = self._find_month_columns(df, month)

            # Находим заголовки дней
            day_headers = self._find_day_headers(df, start_col, end_col)

            # Ищем строку с пользователем
            user_row_idx = None
            name_col_idx = None

            for row_idx in range(len(df)):
                for col_idx in range(
                    min(10, len(df.columns))
                ):  # Ищем имя в первых 10 колонках
                    cell_value = (
                        str(df.iloc[row_idx, col_idx])
                        if pd.notna(df.iloc[row_idx, col_idx])
                        else ""
                    )

                    if fullname in cell_value:
                        user_row_idx = row_idx
                        name_col_idx = col_idx
                        logger.info(
                            f"Найден пользователь '{fullname}' в строке {row_idx}, колонке {col_idx}"
                        )
                        break

                if user_row_idx is not None:
                    break

            if user_row_idx is None:
                raise ValueError(f"Пользователь '{fullname}' не найден в расписании")

            # Извлекаем расписание пользователя
            schedule = {}

            for col_idx in range(start_col, end_col + 1):
                if col_idx in day_headers:
                    day = day_headers[col_idx]
                    schedule_value = (
                        str(df.iloc[user_row_idx, col_idx])
                        if pd.notna(df.iloc[user_row_idx, col_idx])
                        else ""
                    )

                    # Очищаем значение от лишних символов
                    schedule_value = schedule_value.strip()
                    if schedule_value.lower() in ["nan", "none", ""]:
                        schedule_value = "Не указано"

                    schedule[day] = schedule_value

            logger.info(
                f"Получено расписание для '{fullname}' на {month}: {len(schedule)} дней"
            )
            return schedule

        except Exception as e:
            logger.error(
                f"Ошибка при получении расписания для '{fullname}' на {month}: {e}"
            )
            raise


def get_user_schedule(fullname: str, month: str, year: int = None) -> Dict[str, str]:
    """
    Функция-обертка для получения расписания пользователя

    Args:
        fullname: Полное имя пользователя (ФИО)
        month: Название месяца (например, "август", "сентябрь")
        year: Год (по умолчанию текущий)

    Returns:
        Словарь {день: расписание}

    Example:
        >>> schedule = get_user_schedule("Филонова Ксения Андреевна", "август")
        >>> print(schedule)
        {'1 (Пт)': '09:00-21:00', '2 (Сб)': '09:00-21:00', ...}
    """
    parser = ScheduleParser()
    return parser.get_user_schedule(fullname, month, year)


def get_user_schedule_formatted(
    fullname: str, month: str, year: int = None, compact: bool = False
) -> str:
    """
    Получает расписание пользователя в отформатированном виде

    Args:
        fullname: Полное имя пользователя (ФИО)
        month: Название месяца
        year: Год (по умолчанию текущий)
        compact: Компактный формат (True) или полный (False)

    Returns:
        Отформатированная строка с расписанием
    """
    try:
        schedule = get_user_schedule(fullname, month, year)

        if not schedule:
            return f"❌ Расписание для <b>{fullname}</b> на {month} не найдено"

        # Разбираем и группируем расписание
        work_days = []
        days_off = []
        vacation_days = []
        sick_days = []

        for day, time_schedule in schedule.items():
            schedule_clean = time_schedule.strip().upper()

            if not schedule_clean or schedule_clean in [
                "НЕ УКАЗАНО",
                "NAN",
                "NONE",
                "",
            ]:
                days_off.append(day)
            elif "ОТПУСК" in schedule_clean:
                vacation_days.append(day)
            elif any(word in schedule_clean for word in ["БОЛЬНИЧНЫЙ", "Б/Л", "SICK"]):
                sick_days.append(day)
            elif any(char in schedule_clean for char in ["-", ":"]):
                work_days.append((day, time_schedule))
            else:
                # Прочие статусы (командировка, учеба и т.д.)
                work_days.append((day, time_schedule))

        if compact:
            return _format_compact_schedule(
                fullname, month, work_days, days_off, vacation_days, sick_days
            )
        else:
            return _format_detailed_schedule(
                fullname, month, work_days, days_off, vacation_days, sick_days
            )

    except Exception as e:
        logger.error(f"Ошибка при форматировании расписания: {e}")
        return f"❌ <b>Ошибка при получении расписания:</b>\n<code>{e}</code>"


def _format_compact_schedule(
    fullname: str,
    month: str,
    work_days: List[Tuple[str, str]],
    days_off: List[str],
    vacation_days: List[str],
    sick_days: List[str],
) -> str:
    """Компактный формат расписания"""

    lines = [f"<b>👔 Мой график • {month.capitalize()}</b>\n"]

    # Рабочие дни
    if work_days:
        lines.append("🔸 <b>Рабочие:</b>")
        grouped_schedule = _group_consecutive_schedule(work_days)
        for schedule_info in grouped_schedule:
            lines.append(f"{schedule_info}")

    # Отпуск
    if vacation_days:
        vacation_range = _format_day_range(vacation_days)
        lines.append(f"\n🏖 <b>Отпуск:</b> {vacation_range}")

    # Больничные
    if sick_days:
        sick_range = _format_day_range(sick_days)
        lines.append(f"\n🏥 <b>БЛ:</b> {sick_range}")

    # Выходные
    if days_off:
        if len(days_off) <= 3:
            days_str = ", ".join([d.split()[0] for d in days_off])
            lines.append(f"\n🏠 <b>Выходные:</b>\n{days_str}")
        else:
            off_range = _format_day_range(days_off)
            lines.append(f"\n🏠 <b>Выходные:</b>\n{off_range}")

    return "\n".join(lines)


def _format_detailed_schedule(
    fullname: str,
    month: str,
    work_days: List[Tuple[str, str]],
    days_off: List[str],
    vacation_days: List[str],
    sick_days: List[str],
) -> str:
    """Детальный формат расписания"""

    # Красивый заголовок
    lines = [
        "╭─── 📅 <b>РАСПИСАНИЕ</b> ───╮",
        f"│ <b>👤 {_get_short_name(fullname)}</b>",
        f"│ 📆 {month.capitalize()} {datetime.now().year}",
        "╰─────────────────────╯\n",
    ]

    total_work_hours = 0

    # Рабочие дни с подсчетом часов
    if work_days:
        lines.append("⏰ <b>РАБОЧИЕ ДНИ:</b>")
        for day, schedule in work_days:
            hours = _calculate_work_hours(schedule)
            if hours > 0:
                total_work_hours += hours
                lines.append(f"   📌 <b>{day}:</b> <code>{schedule}</code> ({hours}ч)")
            else:
                lines.append(f"   📌 <b>{day}:</b> <code>{schedule}</code>")
        lines.append("")

    # Отпуск
    if vacation_days:
        vacation_range = _format_day_range(vacation_days)
        lines.append(f"🏖 <b>ОТПУСК:</b> {vacation_range}")
        lines.append("")

    # Больничные
    if sick_days:
        sick_range = _format_day_range(sick_days)
        lines.append(f"🏥 <b>БОЛЬНИЧНЫЙ:</b> {sick_range}")
        lines.append("")

    # Выходные дни
    if days_off:
        lines.append("🏠 <b>ВЫХОДНЫЕ ДНИ:</b>")
        if len(days_off) <= 5:
            for day in days_off:
                lines.append(f"   • {day}")
        else:
            off_range = _format_day_range(days_off)
            lines.append(f"   {off_range}")
        lines.append("")

    # Статистика
    work_days_count = len(work_days)
    total_days = len(work_days) + len(days_off) + len(vacation_days) + len(sick_days)

    lines.append("📊 <b>СТАТИСТИКА:</b>")
    lines.append(f"   • Рабочих дней: <b>{work_days_count}</b>")
    if total_work_hours > 0:
        lines.append(f"   • Рабочих часов: <b>{total_work_hours}ч</b>")
    lines.append(f"   • Выходных: <b>{len(days_off)}</b>")
    if vacation_days:
        lines.append(f"   • Отпуск: <b>{len(vacation_days)} дн.</b>")
    if sick_days:
        lines.append(f"   • БЛ: <b>{len(sick_days)} дн.</b>")

    return "\n".join(lines)


def _get_short_name(fullname: str) -> str:
    """Сокращает ФИО до Фамилия И.О."""
    parts = fullname.strip().split()
    if len(parts) >= 3:
        return f"{parts[0]} {parts[1][0]}.{parts[2][0]}."
    elif len(parts) == 2:
        return f"{parts[0]} {parts[1][0]}."
    return fullname


def _group_consecutive_schedule(work_days: List[Tuple[str, str]]) -> List[str]:
    """Группирует последовательные дни с одинаковым расписанием"""
    if not work_days:
        return []

    schedule_groups = {}
    for day, schedule in work_days:
        if schedule not in schedule_groups:
            schedule_groups[schedule] = []
        day_num = day.split()[0]  # Извлекаем только номер дня
        schedule_groups[schedule].append(day_num)

    result = []
    for schedule, days in schedule_groups.items():
        if len(days) == 1:
            result.append(f"{days[0]} → <code>{schedule}</code>")
        else:
            days_range = _format_consecutive_days(days)
            result.append(f"{days_range} → <code>{schedule}</code>")

    return result


def _format_consecutive_days(days: List[str]) -> str:
    """Форматирует последовательные дни в диапазоны"""
    if not days:
        return ""

    # Сортируем дни по числовому значению
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
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = end = day

    # Добавляем последний диапазон
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")

    return ", ".join(ranges)


def _format_day_range(days: List[str]) -> str:
    """Форматирует диапазон дней"""
    if not days:
        return ""

    day_numbers = []
    for day in days:
        day_num = day.split()[0]  # Берем только номер дня
        try:
            day_numbers.append(int(day_num))
        except ValueError:
            continue

    if not day_numbers:
        return ", ".join([d.split()[0] for d in days])

    return _format_consecutive_days([str(d) for d in day_numbers])


def _calculate_work_hours(schedule: str) -> float:
    """Вычисляет количество рабочих часов из расписания"""

    # Ищем паттерн времени вида "09:00-21:00"
    time_pattern = r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})"
    match = re.search(time_pattern, schedule)

    if match:
        start_hour, start_min, end_hour, end_min = map(int, match.groups())
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min

        # Обработка случая, когда конец на следующий день
        if end_minutes < start_minutes:
            end_minutes += 24 * 60

        work_minutes = end_minutes - start_minutes
        return round(work_minutes / 60, 1)

    return 0

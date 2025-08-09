import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import pytz

logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    """Типы расписаний"""

    REGULAR = "regular"
    DUTIES = "duties"
    HEADS = "heads"


@dataclass
class HeadInfo:
    """Информация о руководителе группы"""

    name: str
    schedule: str
    duty_info: Optional[str] = None  # Информация о дежурстве, если есть


@dataclass
class DayInfo:
    """Информация о дне в расписании"""

    day: str
    schedule: str
    work_hours: int = 0

    @property
    def day_number(self) -> int:
        """Извлекает номер дня"""
        try:
            return int(self.day.split()[0])
        except (ValueError, IndexError):
            return 0


@dataclass
class ScheduleStats:
    """Статистика расписания"""

    total_work_days: int
    total_work_hours: float
    vacation_days: int
    sick_days: int
    days_off: int
    missing_days: int
    total_days: int


@dataclass
class DutyInfo:
    """Информация о дежурстве"""

    name: str
    schedule: str
    shift_type: str  # "П" или "С" или ""
    work_hours: str


class ScheduleFileManager:
    """Менеджер для работы с файлами расписаний"""

    def __init__(self, uploads_folder: str = "uploads"):
        self.uploads_folder = Path(uploads_folder)

    def find_schedule_file(
        self, division: str, schedule_type: ScheduleType = ScheduleType.REGULAR
    ) -> Optional[Path]:
        """
        Ищет файл расписания по подразделению (НТП1, НТП2, НЦК и т.д.)

        Args:
            division: Подразделение из БД (НТП1, НТП2, НЦК, etc.)
            schedule_type: Тип расписания

        Returns:
            Path к найденному файлу или None
        """
        try:
            patterns = [
                f"ГРАФИК {division} I*",
                f"ГРАФИК {division} II*",
                f"ГРАФИК_{division}_*",
                f"*{division}*ГРАФИК*",
            ]

            # Ищем файлы по паттернам
            for pattern in patterns:
                files = list(self.uploads_folder.glob(pattern))
                if files:
                    # Выбираем самый свежий файл, если их несколько
                    latest_file = max(files, key=lambda f: f.stat().st_mtime)
                    logger.debug(f"Найден файл расписания: {latest_file}")
                    return latest_file

            logger.error(
                f"Файл расписания {division} ({schedule_type.value}) не найден в {self.uploads_folder}"
            )
            return None

        except Exception as e:
            logger.error(f"Ошибка при поиске файла расписания: {e}")
            return None


class MonthManager:
    """Менеджер для работы с месяцами"""

    MONTH_MAPPING = {
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

    MONTHS_ORDER = [
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

    @classmethod
    def normalize_month(cls, month: str) -> str:
        """Нормализует название месяца"""
        return cls.MONTH_MAPPING.get(month.lower(), month.upper())

    @classmethod
    def get_available_months(cls) -> List[str]:
        """Возвращает список доступных месяцев"""
        return [month.lower() for month in cls.MONTHS_ORDER]


class ExcelParser:
    """Парсер Excel файлов"""

    def __init__(self, file_manager: ScheduleFileManager):
        self.file_manager = file_manager

    def read_excel_file(
        self, file_path: Path, schedule_type: ScheduleType = ScheduleType.REGULAR
    ) -> pd.DataFrame:
        """
        Читает Excel файл с обработкой различных листов

        Args:
            file_path: Путь к файлу
            schedule_type: Тип расписания

        Returns:
            DataFrame с данными
        """
        # Возможные имена листов в зависимости от типа расписания
        if schedule_type == ScheduleType.DUTIES:
            sheet_names = [
                "ДЕЖУРСТВА",
                "Дежурства",
                "СТАРШИЕ",
                "Старшие",
                "ГРАФИК",
                "График",
                "Sheet1",
                0,
            ]
        elif schedule_type == ScheduleType.HEADS:
            sheet_names = [
                "РГ",
                "РУКОВОДИТЕЛИ",
                "Руководители",
                "ГРАФИК",
                "График",
                "Sheet1",
                0,
            ]
        else:
            sheet_names = ["ГРАФИК", "График", "график", "Sheet1", 0]

        for sheet_name in sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
                logger.debug(f"Успешно прочитан лист: {sheet_name}")
                return df
            except Exception as e:
                logger.debug(f"Не удалось прочитать лист '{sheet_name}': {e}")
                continue

        raise ValueError(f"Не удалось прочитать ни один лист из файла {file_path}")

    def find_month_columns(self, df: pd.DataFrame, month: str) -> Tuple[int, int]:
        """Находит колонки для указанного месяца"""
        month = MonthManager.normalize_month(month)

        # Ищем начало месяца
        month_start_col = self._find_month_start(df, month)
        if month_start_col is None:
            raise ValueError(f"Месяц '{month}' не найден в файле")

        # Ищем конец месяца
        month_end_col = self._find_month_end(df, month, month_start_col)

        logger.debug(
            f"Месяц '{month}' найден в колонках {month_start_col}-{month_end_col}"
        )
        return month_start_col, month_end_col

    def _find_month_start(self, df: pd.DataFrame, month: str) -> Optional[int]:
        """Ищет начальную колонку месяца"""
        # Поиск в заголовках колонок
        for col_idx, col in enumerate(df.columns):
            if isinstance(col, str) and month in col.upper():
                return col_idx

        # Поиск в первых строках
        for row_idx in range(min(5, len(df))):
            for col_idx, cell_value in enumerate(df.iloc[row_idx]):
                if isinstance(cell_value, str) and month in cell_value.upper():
                    return col_idx

        return None

    def _find_month_end(
        self, df: pd.DataFrame, current_month: str, start_col: int
    ) -> int:
        """Ищет конечную колонку месяца"""
        month_end_col = len(df.columns) - 1

        # Ищем следующий месяц
        for col_idx in range(start_col + 1, len(df.columns)):
            # Проверяем заголовок колонки
            col_name = (
                str(df.columns[col_idx]) if df.columns[col_idx] is not None else ""
            )

            for month in MonthManager.MONTHS_ORDER:
                if month != current_month and month in col_name.upper():
                    return col_idx - 1

            # Проверяем содержимое ячеек
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
        """Находит заголовки дней"""
        day_headers = {}

        for row_idx in range(min(5, len(df))):
            for col_idx in range(start_col, end_col + 1):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )

                # Паттерн для дней: "1Пт", "2Сб", etc.
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

        logger.debug(f"Найдено {len(day_headers)} дней в заголовках")
        return day_headers

    def find_user_row(self, df: pd.DataFrame, fullname: str) -> Optional[int]:
        """Находит строку пользователя"""
        for row_idx in range(len(df)):
            for col_idx in range(min(3, len(df.columns))):  # Ищем в первых 3 колонках
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )

                if fullname in cell_value:
                    logger.debug(f"Пользователь '{fullname}' найден в строке {row_idx}")
                    return row_idx

        return None


class ScheduleAnalyzer:
    """Анализатор расписаний"""

    @staticmethod
    def categorize_schedule_entry(schedule_value: str) -> str:
        """Категоризирует запись расписания"""
        schedule_clean = schedule_value.strip().upper()

        if not schedule_clean or schedule_clean in ["НЕ УКАЗАНО", "NAN", "NONE", ""]:
            return "day_off"
        elif "ОТПУСК" in schedule_clean:
            return "vacation"
        elif "Н" in schedule_clean:
            return "missing"
        elif any(word in schedule_clean for word in ["ЛНТС"]):
            return "sick"
        elif any(char in schedule_clean for char in ["-", ":"]):
            return "work"
        else:
            return "work"  # Прочие рабочие статусы

    @staticmethod
    def calculate_work_hours(schedule: str) -> float:
        """Вычисляет рабочие часы из расписания"""
        time_pattern = r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})"
        match = re.search(time_pattern, schedule)

        if not match:
            return 0.0

        start_hour, start_min, end_hour, end_min = map(int, match.groups())
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min

        # Обработка перехода через полночь
        if end_minutes < start_minutes:
            end_minutes += 24 * 60

        work_minutes = end_minutes - start_minutes
        work_hours = work_minutes / 60

        # Вычитаем обеденный перерыв для длинных смен
        if work_hours >= 8:
            work_hours -= 1

        return round(work_hours, 1)

    @staticmethod
    def analyze_schedule(
        schedule_data: Dict[str, str],
    ) -> tuple[list[Any], list[Any], list[Any], list[Any], list[Any]]:
        """
        Анализирует расписание и разделяет по категориям

        Returns:
            Tuple: (work_days, days_off, vacation_days, sick_days)
        """
        work_days = []
        days_off = []
        vacation_days = []
        missing_days = []
        sick_days = []

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
            elif category == "sick":
                sick_days.append(day_info)
            elif category == "missing":
                missing_days.append(day_info)
            else:  # day_off
                days_off.append(day_info)

        return work_days, days_off, vacation_days, sick_days, missing_days


class ScheduleFormatter:
    """Форматировщик расписаний"""

    @staticmethod
    def format_compact(
        month: str,
        work_days: List[DayInfo],
        days_off: List[DayInfo],
        vacation_days: List[DayInfo],
        sick_days: List[DayInfo],
        missing_days: List[DayInfo],
    ) -> str:
        """Компактный формат расписания"""
        lines = [f"<b>👔 Мой график • {month.capitalize()}</b>\n"]

        # Рабочие дни
        if work_days:
            lines.append("🔸 <b>Рабочие:</b>")
            grouped_schedule = ScheduleFormatter._group_consecutive_schedule(work_days)
            lines.extend(grouped_schedule)

        # Отпуск
        if vacation_days:
            vacation_range = ScheduleFormatter._format_day_range(
                [d.day for d in vacation_days]
            )
            lines.append(f"\n🏖 <b>Отпуск:</b> {vacation_range}")

        # Больничные
        if sick_days:
            sick_range = ScheduleFormatter._format_day_range([d.day for d in sick_days])
            lines.append(f"\n🏥 <b>БЛ:</b> {sick_range}")

        # Отсутствия на смене
        if missing_days:
            missing_range = ScheduleFormatter._format_day_range(
                [d.day for d in missing_days]
            )
            lines.append(f"\n🕵️‍♂️ <b>Отсутствия:</b> {missing_range}")

        # Выходные
        if days_off:
            if len(days_off) <= 3:
                days_str = ", ".join([d.day.split()[0] for d in days_off])
                lines.append(f"\n🏠 <b>Выходные:</b>\n{days_str}")
            else:
                off_range = ScheduleFormatter._format_day_range(
                    [d.day for d in days_off]
                )
                lines.append(f"\n🏠 <b>Выходные:</b>\n{off_range}")
        message_to_send = "\n".join(lines)
        message_to_send += "\n\n<i>Перечисление указано в числах месяца</i>"
        return "\n".join(lines)

    @staticmethod
    def format_detailed(
        month: str,
        work_days: List[DayInfo],
        days_off: List[DayInfo],
        vacation_days: List[DayInfo],
        sick_days: List[DayInfo],
        missing_range: List[DayInfo],
    ) -> str:
        """Детальный формат расписания - показывает расписание день за днем"""
        lines = [f"<b>👔 Мой график • {month.capitalize()}</b>\n"]

        # Объединяем все дни в один список для сортировки
        all_days = []

        # Добавляем рабочие дни
        for day_info in work_days:
            all_days.append((day_info, "work"))

        # Добавляем выходные
        for day_info in days_off:
            all_days.append((day_info, "day_off"))

        # Добавляем отпуск
        for day_info in vacation_days:
            all_days.append((day_info, "vacation"))

        # Добавляем больничные
        for day_info in sick_days:
            all_days.append((day_info, "sick"))

        # Добавляем отсутствия
        for day_info in missing_range:
            all_days.append((day_info, "missing"))

        # Сортируем по дню (извлекаем число из строки дня)
        def extract_day_number(day_str: str) -> int:
            """Извлекает номер дня из строки вида '4 (Пн)' или '4'"""
            try:
                return int(day_str.split()[0])
            except (ValueError, IndexError):
                return 0

        all_days.sort(key=lambda x: extract_day_number(x[0].day))

        # Выводим расписание день за днем
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

        # Статистика
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
    def _format_statistics(stats: ScheduleStats) -> List[str]:
        """Форматирует статистику"""
        lines = ["<blockquote expandable>📊 <b>Статистика:</b>"]
        lines.append(f"Рабочих дней: <b>{stats.total_work_days}</b>")

        if stats.total_work_hours > 0:
            lines.append(f"Рабочих часов: <b>{stats.total_work_hours}ч</b>")

        lines.append(f"Выходных: <b>{stats.days_off}</b>")

        if stats.vacation_days:
            lines.append(f"Отпуск: <b>{stats.vacation_days} дн.</b>")

        if stats.missing_days:
            lines.append(f"Отсутствий: <b>{stats.missing_days} дн.</b>")

        if stats.sick_days:
            lines.append(f"БЛ: <b>{stats.sick_days} дн.</b>")

        lines.append("</blockquote>")
        return lines

    @staticmethod
    def _group_consecutive_schedule(work_days: List[DayInfo]) -> List[str]:
        """Группирует последовательные дни с одинаковым расписанием"""
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
        """Форматирует последовательные дни"""
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
    def _format_day_range(days: List[DayInfo] | List[str]) -> str:
        """Форматирует диапазон дней"""
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


class ScheduleParser:
    """Главный класс парсера расписаний"""

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
        """
        Получает расписание пользователя

        Args:
            fullname: ФИО пользователя
            month: Месяц
            division: Подразделение из БД (НТП1, НТП2, НЦК, etc.)
            schedule_type: Тип расписания

        Returns:
            Словарь {день: расписание}
        """
        try:
            # Находим файл
            schedule_file = self.file_manager.find_schedule_file(
                division, schedule_type
            )
            if not schedule_file:
                raise FileNotFoundError(f"Файл расписания {division} не найден")

            # Читаем файл
            df = self.excel_parser.read_excel_file(schedule_file, schedule_type)

            # Находим колонки месяца
            start_col, end_col = self.excel_parser.find_month_columns(df, month)

            # Находим заголовки дней
            day_headers = self.excel_parser.find_day_headers(df, start_col, end_col)

            # Находим строку пользователя
            user_row_idx = self.excel_parser.find_user_row(df, fullname)
            if user_row_idx is None:
                raise ValueError(f"Пользователь {fullname} не найден в расписании")

            # Извлекаем расписание
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
                f"Получено расписание для '{fullname}' на {month}: {len(schedule)} дней"
            )
            return schedule

        except Exception as e:
            logger.error(f"Ошибка при получении расписания: {e}")
            raise

    def get_user_schedule_formatted(
        self,
        fullname: str,
        month: str,
        division: str,
        compact: bool = False,
        schedule_type: ScheduleType = ScheduleType.REGULAR,
    ) -> str:
        """
        Получает отформатированное расписание пользователя

        Args:
            fullname: ФИО пользователя
            month: Месяц
            division: Подразделение из БД (НТП1, НТП2, НЦК, etc.)
            compact: Компактный формат
            schedule_type: Тип расписания

        Returns:
            Отформатированная строка с расписанием
        """
        try:
            schedule_data = self.get_user_schedule(
                fullname, month, division, schedule_type
            )

            if not schedule_data:
                return f"❌ Расписание для <b>{fullname}</b> на {month} не найдено"

            # Анализируем расписание
            work_days, days_off, vacation_days, sick_days, missing_days = (
                self.analyzer.analyze_schedule(schedule_data)
            )

            # Форматируем результат
            if compact:
                return self.formatter.format_compact(
                    month, work_days, days_off, vacation_days, sick_days, missing_days
                )
            else:
                return self.formatter.format_detailed(
                    month, work_days, days_off, vacation_days, sick_days, missing_days
                )

        except Exception as e:
            logger.error(f"Ошибка при форматировании расписания: {e}")
            return f"❌ <b>Ошибка при получении расписания:</b>\n<code>{e}</code>"


class DutyScheduleParser(ScheduleParser):
    """Парсер для расписания дежурств"""

    def __init__(self, uploads_folder: str = "uploads"):
        super().__init__(uploads_folder)
        self.yekaterinburg_tz = pytz.timezone("Asia/Yekaterinburg")

    def get_current_yekaterinburg_date(self) -> datetime:
        """Получает текущую дату по Екатеринбургу"""
        return datetime.now(self.yekaterinburg_tz)

    def get_duty_sheet_name(self, date: datetime) -> str:
        """Генерирует название листа дежурств для указанной даты"""
        month_names = [
            "Январь",
            "Февраль",
            "Март",
            "Апрель",
            "Май",
            "Июнь",
            "Июль",
            "Август",
            "Сентябрь",
            "Октябрь",
            "Ноябрь",
            "Декабрь",
        ]
        month_name = month_names[date.month - 1]
        return f"Дежурство {month_name}"

    def find_date_column(
        self, df: pd.DataFrame, target_date: datetime
    ) -> Optional[int]:
        """Находит колонку с указанной датой"""
        target_day = target_date.day

        # Ищем в первых нескольких строках заголовок с датами
        for row_idx in range(min(3, len(df))):
            for col_idx in range(len(df.columns)):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )

                # Ищем паттерн вида "1Пт", "15Сб" и т.д.
                day_pattern = r"^(\d{1,2})[А-Яа-я]{1,2}$"
                match = re.search(day_pattern, cell_value.strip())

                if match and int(match.group(1)) == target_day:
                    logger.debug(f"Найдена колонка даты {target_day}: {col_idx}")
                    return col_idx

        logger.warning(f"Колонка для даты {target_day} не найдена")
        return None

    def parse_duty_entry(self, cell_value: str) -> Tuple[str, str]:
        """
        Парсит запись дежурства и извлекает тип смены и время

        Args:
            cell_value: Значение ячейки (например, "П 15:00-21:00", "С 09:00-15:00", "21:00-09:00")

        Returns:
            Tuple: (shift_type, schedule)
        """
        if not cell_value or cell_value.strip() in ["", "nan", "None"]:
            return "", ""

        cell_value = cell_value.strip()

        # Проверяем наличие префикса П или С
        if cell_value.startswith("П "):
            return "П", cell_value[2:].strip()
        elif cell_value.startswith("С "):
            return "С", cell_value[2:].strip()
        else:
            # Если префикса нет, но есть время - это обычное дежурство
            if re.search(r"\d{1,2}:\d{2}-\d{1,2}:\d{2}", cell_value):
                return "", cell_value
            else:
                return "", cell_value

    def get_duties_for_date(self, date: datetime, division: str) -> List[DutyInfo]:
        """
        Получает список дежурных на указанную дату

        Args:
            date: Дата
            division: Подразделение

        Returns:
            Список дежурных с их расписанием
        """
        try:
            # Находим файл дежурств
            schedule_file = self.file_manager.find_schedule_file(
                division, ScheduleType.DUTIES
            )
            if not schedule_file:
                raise FileNotFoundError(f"Файл дежурств {division} не найден")

            # Получаем название листа
            sheet_name = self.get_duty_sheet_name(date)

            # Читаем файл
            try:
                df = pd.read_excel(schedule_file, sheet_name=sheet_name, header=None)
            except Exception:
                # Если лист не найден, пробуем с английским названием
                english_months = {
                    1: "January",
                    2: "February",
                    3: "March",
                    4: "April",
                    5: "May",
                    6: "June",
                    7: "July",
                    8: "August",
                    9: "September",
                    10: "October",
                    11: "November",
                    12: "December",
                }
                alt_sheet_name = f"Дежурство {english_months[date.month]}"
                df = pd.read_excel(
                    schedule_file, sheet_name=alt_sheet_name, header=None
                )

            # Находим колонку с нужной датой
            date_col = self.find_date_column(df, date)
            if date_col is None:
                logger.warning(f"Дата {date.day} не найдена в расписании дежурств")
                return []

            duties = []

            # Проходим по всем строкам и ищем дежурных
            for row_idx in range(len(df)):
                # Проверяем первые несколько колонок на наличие ФИО
                name = ""
                for col_idx in range(min(3, len(df.columns))):
                    cell_value = (
                        str(df.iloc[row_idx, col_idx])
                        if pd.notna(df.iloc[row_idx, col_idx])
                        else ""
                    )

                    # Простая проверка на ФИО (содержит буквы и минимум 3 слова)
                    if (
                        len(cell_value.split()) >= 3
                        and re.search(r"[А-Яа-я]", cell_value)
                        and not re.search(r"\d", cell_value)
                    ):
                        name = cell_value.strip()
                        break

                if not name:
                    continue

                # Получаем расписание для этой даты
                if date_col < len(df.columns):
                    duty_cell = (
                        str(df.iloc[row_idx, date_col])
                        if pd.notna(df.iloc[row_idx, date_col])
                        else ""
                    )

                    if duty_cell and duty_cell.strip() not in ["", "nan", "None"]:
                        shift_type, schedule = self.parse_duty_entry(duty_cell)

                        # Добавляем только если есть маркер смены (С или П) в оригинальной ячейке
                        # Это означает, что человек действительно дежурит в этот день
                        if shift_type in ["С", "П"] and re.search(
                            r"\d{1,2}:\d{2}-\d{1,2}:\d{2}", schedule
                        ):
                            duties.append(
                                DutyInfo(
                                    name=name,
                                    schedule=schedule,
                                    shift_type=shift_type,
                                    work_hours=schedule,
                                )
                            )

            logger.info(
                f"Найдено {len(duties)} дежурных на {date.strftime('%d.%m.%Y')}"
            )
            return duties

        except Exception as e:
            logger.error(f"Ошибка при получении дежурств: {e}")
            return []

    def get_gender_emoji(self, name: str) -> str:
        """
        Определяет пол по имени (простая эвристика)

        Args:
            name: ФИО

        Returns:
            Эмодзи для пола
        """
        # Простая проверка по окончанию отчества
        parts = name.split()
        if len(parts) >= 3:
            patronymic = parts[2]
            if patronymic.endswith("на"):
                return "👩‍🦰"
            elif (
                patronymic.endswith("ич")
                or patronymic.endswith("ович")
                or patronymic.endswith("евич")
            ):
                return "👨"

        # По умолчанию мужской
        return "👨"

    def parse_time_range(self, time_str: str) -> Tuple[int, int]:
        """
        Парсит временной диапазон и возвращает начальное время в минутах

        Args:
            time_str: Строка времени вида "15:00-21:00"

        Returns:
            Tuple: (start_minutes, end_minutes)
        """
        try:
            if "-" not in time_str:
                return 0, 0

            start_time, end_time = time_str.split("-")

            start_parts = start_time.strip().split(":")
            end_parts = end_time.strip().split(":")

            start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
            end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])

            # Обработка перехода через полночь
            if end_minutes < start_minutes:
                end_minutes += 24 * 60

            return start_minutes, end_minutes

        except (ValueError, IndexError):
            return 0, 0

    def format_duties_for_date(self, date: datetime, duties: List[DutyInfo]) -> str:
        """
        Форматирует список дежурных для отображения, группируя по времени

        Args:
            date: Дата
            duties: Список дежурных

        Returns:
            Отформатированная строка
        """
        if not duties:
            return f"<b>👮‍♂️ Дежурные • {date.strftime('%d.%m.%Y')}</b>\n\n❌ Дежурных на эту дату не найдено"

        lines = [f"<b>👮‍♂️ Дежурные • {date.strftime('%d.%m.%Y')}</b>\n"]

        # Группируем дежурных по времени
        time_groups = {}

        for duty in duties:
            # Извлекаем время работы
            time_schedule = duty.schedule
            if not time_schedule or not re.search(
                r"\d{1,2}:\d{2}-\d{1,2}:\d{2}", time_schedule
            ):
                continue

            if time_schedule not in time_groups:
                time_groups[time_schedule] = {
                    "duties": [],  # Старшие (С)
                    "helpers": [],  # Помощники (П)
                }

            if duty.shift_type == "С":
                time_groups[time_schedule]["duties"].append(duty)
            elif duty.shift_type == "П":
                time_groups[time_schedule]["helpers"].append(duty)
            else:
                # Если нет префикса, считаем обычным дежурным
                time_groups[time_schedule]["duties"].append(duty)

        # Сортируем время по началу смены
        sorted_times = sorted(
            time_groups.keys(), key=lambda t: self.parse_time_range(t)[0]
        )

        for time_schedule in sorted_times:
            group = time_groups[time_schedule]

            # Заголовок времени
            lines.append(f"⏰ <b>{time_schedule}</b>")

            # Старшие
            for duty in group["duties"]:
                gender_emoji = self.get_gender_emoji(duty.name)
                lines.append(f"{gender_emoji}Старший - {duty.name}")

            # Помощники
            for duty in group["helpers"]:
                gender_emoji = self.get_gender_emoji(duty.name)
                lines.append(f"{gender_emoji}Помощник - {duty.name}")

            lines.append("")  # Пустая строка между временными блоками

        # Убираем последнюю пустую строку
        if lines and lines[-1] == "":
            lines.pop()

        return "\n".join(lines)


class HeadScheduleParser(ScheduleParser):
    """Парсер для расписания руководителей групп"""

    def __init__(self, uploads_folder: str = "uploads"):
        super().__init__(uploads_folder)
        self.yekaterinburg_tz = pytz.timezone("Asia/Yekaterinburg")

    def get_current_yekaterinburg_date(self) -> datetime:
        """Получает текущую дату по Екатеринбургу"""
        return datetime.now(self.yekaterinburg_tz)

    def find_date_column(
        self, df: pd.DataFrame, target_date: datetime
    ) -> Optional[int]:
        """Находит колонку с указанной датой"""
        target_day = target_date.day

        # Ищем в первых нескольких строках заголовок с датами
        for row_idx in range(min(5, len(df))):
            for col_idx in range(len(df.columns)):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )

                # Ищем паттерн вида "1Пт", "15Сб" и т.д.
                day_pattern = r"^(\d{1,2})[А-Яа-я]{1,2}$"
                match = re.search(day_pattern, cell_value.strip())

                if match and int(match.group(1)) == target_day:
                    logger.debug(f"Найдена колонка даты {target_day}: {col_idx}")
                    return col_idx

        logger.warning(f"Колонка для даты {target_day} не найдена")
        return None

    def get_heads_for_date(self, date: datetime, division: str) -> List[HeadInfo]:
        """
        Получает список руководителей групп на указанную дату

        Args:
            date: Дата
            division: Подразделение

        Returns:
            Список руководителей с их расписанием
        """
        try:
            # Находим файл расписания (обычный ГРАФИК)
            schedule_file = self.file_manager.find_schedule_file(
                division, ScheduleType.REGULAR
            )
            if not schedule_file:
                raise FileNotFoundError(f"Файл расписания {division} не найден")

            # Читаем файл
            df = pd.read_excel(schedule_file, sheet_name="ГРАФИК", header=None)

            # Находим колонку с нужной датой
            date_col = self.find_date_column(df, date)
            if date_col is None:
                logger.warning(f"Дата {date.day} не найдена в расписании")
                return []

            heads = []

            # Проходим по всем строкам и ищем руководителей групп
            for row_idx in range(len(df)):
                # Ищем метку "Руководитель группы" в строке
                position_found = False
                name = ""

                for col_idx in range(min(10, len(df.columns))):
                    cell_value = (
                        str(df.iloc[row_idx, col_idx])
                        if pd.notna(df.iloc[row_idx, col_idx])
                        else ""
                    )

                    # Проверяем на должность
                    if "Руководитель группы" in cell_value:
                        position_found = True

                    # Извлекаем ФИО (обычно в первых колонках)
                    if (
                        not name
                        and len(cell_value.split()) >= 3
                        and re.search(r"[А-Яа-я]", cell_value)
                        and "Руководитель" not in cell_value
                    ):
                        name = cell_value.strip()

                if not position_found or not name:
                    continue

                # Получаем расписание для этой даты
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
                        # Проверяем, есть ли рабочее время
                        if re.search(r"\d{1,2}:\d{2}-\d{1,2}:\d{2}", schedule_cell):
                            # Проверяем, есть ли дежурство в тот же день
                            duty_info = self._check_duty_for_head(name, date, division)

                            heads.append(
                                HeadInfo(
                                    name=name,
                                    schedule=schedule_cell.strip(),
                                    duty_info=duty_info,
                                )
                            )

            logger.info(
                f"Найдено {len(heads)} руководителей групп на {date.strftime('%d.%m.%Y')}"
            )
            return heads

        except Exception as e:
            logger.error(f"Ошибка при получении руководителей групп: {e}")
            return []

    def _check_duty_for_head(
        self, head_name: str, date: datetime, division: str
    ) -> Optional[str]:
        """
        Проверяет, дежурит ли руководитель в указанную дату

        Args:
            head_name: ФИО руководителя
            date: Дата
            division: Подразделение

        Returns:
            Информация о дежурстве или None
        """
        try:
            # Используем DutyScheduleParser для проверки дежурств
            duty_parser = DutyScheduleParser()
            duties = duty_parser.get_duties_for_date(date, division)

            for duty in duties:
                # Проверяем по ФИО (может быть частичное совпадение)
                if self._names_match(head_name, duty.name):
                    return f"{duty.schedule} [{duty.shift_type}]"

            return None

        except Exception as e:
            logger.debug(f"Ошибка при проверке дежурства для {head_name}: {e}")
            return None

    def _names_match(self, name1: str, name2: str) -> bool:
        """
        Проверяет совпадение имен (учитывает различия в написании)

        Args:
            name1: Первое имя
            name2: Второе имя

        Returns:
            True если имена совпадают
        """
        # Простая проверка по фамилии и имени
        parts1 = name1.split()
        parts2 = name2.split()

        if len(parts1) >= 2 and len(parts2) >= 2:
            return parts1[0] == parts2[0] and parts1[1] == parts2[1]

        return False

    def get_gender_emoji(self, name: str) -> str:
        """
        Определяет пол по имени (простая эвристика)

        Args:
            name: ФИО

        Returns:
            Эмодзи для пола
        """
        # Простая проверка по окончанию отчества
        parts = name.split()
        if len(parts) >= 3:
            patronymic = parts[2]
            if patronymic.endswith("на"):
                return "👩‍💼"
            elif (
                patronymic.endswith("ич")
                or patronymic.endswith("ович")
                or patronymic.endswith("евич")
            ):
                return "👨‍💼"

        # По умолчанию мужской
        return "👨‍💼"

    def format_heads_for_date(self, date: datetime, heads: List[HeadInfo]) -> str:
        """
        Форматирует список руководителей групп для отображения

        Args:
            date: Дата
            heads: Список руководителей

        Returns:
            Отформатированная строка
        """
        if not heads:
            return f"<b>👑 Руководители групп • {date.strftime('%d.%m.%Y')}</b>\n\n❌ Руководители групп на эту дату не найдены"

        lines = [f"<b>👑 Руководители групп • {date.strftime('%d.%m.%Y')}</b>\n"]

        # Группируем по времени работы
        time_groups = {}

        for head in heads:
            # Извлекаем время работы
            time_schedule = head.schedule
            if not time_schedule or not re.search(
                r"\d{1,2}:\d{2}-\d{1,2}:\d{2}", time_schedule
            ):
                continue

            # Извлекаем только время
            time_match = re.search(r"(\d{1,2}:\d{2}-\d{1,2}:\d{2})", time_schedule)
            if time_match:
                time_key = time_match.group(1)
            else:
                time_key = time_schedule

            if time_key not in time_groups:
                time_groups[time_key] = []

            time_groups[time_key].append(head)

        # Сортируем время по началу смены
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

            # Заголовок времени
            lines.append(f"⏰ <b>{time_schedule}</b>")

            # Список руководителей
            for head in group_heads:
                gender_emoji = self.get_gender_emoji(head.name)

                # Формируем строку с руководителем
                head_line = f"{gender_emoji} {head.name}"

                # Добавляем информацию о дежурстве если есть
                if head.duty_info:
                    head_line += f" ({head.duty_info})"

                lines.append(head_line)

            lines.append("")  # Пустая строка между временными блоками

        # Убираем последнюю пустую строку
        if lines and lines[-1] == "":
            lines.pop()

        return "\n".join(lines)


# Публичные функции для обратной совместимости
def get_user_schedule(fullname: str, month: str, division: str) -> Dict[str, str]:
    """
    Функция-обертка для получения расписания пользователя

    Args:
        fullname: Полное имя пользователя (ФИО)
        month: Название месяца
        division: Подразделение из БД (НТП1, НТП2, НЦК, etc.)

    Returns:
        Словарь {день: расписание}
    """
    parser = ScheduleParser()
    return parser.get_user_schedule(fullname, month, division)


def get_user_schedule_formatted(
    fullname: str, month: str, division: str, compact: bool = False
) -> str:
    """
    Получает расписание пользователя в отформатированном виде

    Args:
        fullname: Полное имя пользователя (ФИО)
        month: Название месяца
        division: Подразделение из БД (НТП1, НТП2, НЦК, etc.)
        compact: Компактный формат (True) или полный (False)

    Returns:
        Отформатированная строка с расписанием
    """
    parser = ScheduleParser()
    return parser.get_user_schedule_formatted(fullname, month, division, compact)


# Дополнительные функции для новых типов расписаний
def get_duties_schedule(
    fullname: str, month: str, division: str, compact: bool = False
) -> str:
    """
    Получает расписание дежурств для пользователя

    Args:
        fullname: Полное имя пользователя (ФИО)
        month: Название месяца
        division: Подразделение из БД (НТП1, НТП2, НЦК, etc.)
        compact: Компактный формат (True) или полный (False)

    Returns:
        Отформатированная строка с расписанием дежурств
    """
    parser = ScheduleParser()
    return parser.get_user_schedule_formatted(
        fullname, month, division, compact, ScheduleType.DUTIES
    )


def get_heads_schedule(
    fullname: str, month: str, division: str, compact: bool = False
) -> str:
    """
    Получает расписание руководителей групп

    Args:
        fullname: Полное имя пользователя (ФИО)
        month: Название месяца
        division: Подразделение из БД (НТП1, НТП2, НЦК, etc.)
        compact: Компактный формат (True) или полный (False)

    Returns:
        Отформатированная строка с расписанием РГ
    """
    parser = ScheduleParser()
    return parser.get_user_schedule_formatted(
        fullname, month, division, compact, ScheduleType.HEADS
    )


def get_available_months() -> List[str]:
    """
    Получает список доступных месяцев

    Returns:
        Список доступных месяцев
    """
    return MonthManager.get_available_months()


# Дополнительные утилиты
class ScheduleUtils:
    """Утилиты для работы с расписаниями"""

    @staticmethod
    def get_short_name(fullname: str) -> str:
        """Сокращает ФИО до Фамилия И.О."""
        parts = fullname.strip().split()
        if len(parts) >= 3:
            return f"{parts[0]} {parts[1][0]}.{parts[2][0]}."
        elif len(parts) == 2:
            return f"{parts[0]} {parts[1][0]}."
        return fullname

    @staticmethod
    def validate_month(month: str) -> bool:
        """Проверяет валидность месяца"""
        normalized = MonthManager.normalize_month(month)
        return normalized in MonthManager.MONTHS_ORDER

    @staticmethod
    def validate_division(division: str) -> bool:
        """Проверяет валидность подразделения (НТП1, НТП2, НЦК, etc.)"""
        return "НТП" in division.upper() or "НЦК" in division.upper()

    @staticmethod
    def get_base_division(division: str) -> str:
        """Получает базовое подразделение (НТП или НЦК) из полного названия"""
        return "НТП" if "НТП" in division.upper() else "НЦК"

    @staticmethod
    def get_file_info(
        division: str, schedule_type: ScheduleType = ScheduleType.REGULAR
    ) -> Optional[Dict[str, any]]:
        """
        Получает информацию о файле расписания

        Args:
            division: Подразделение из БД (НТП1, НТП2, НЦК, etc.)
            schedule_type: Тип расписания

        Returns:
            Словарь с информацией о файле или None
        """
        try:
            file_manager = ScheduleFileManager()
            file_path = file_manager.find_schedule_file(division, schedule_type)

            if not file_path:
                return None

            stat = file_path.stat()
            return {
                "path": str(file_path),
                "name": file_path.name,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "exists": file_path.exists(),
            }
        except Exception as e:
            logger.error(f"Ошибка при получении информации о файле: {e}")
            return None


# Исключения для лучшей обработки ошибок
class ScheduleError(Exception):
    """Базовое исключение для ошибок расписания"""

    pass


class ScheduleFileNotFoundError(ScheduleError):
    """Файл расписания не найден"""

    pass


class UserNotFoundError(ScheduleError):
    """Пользователь не найден в расписании"""

    pass


class MonthNotFoundError(ScheduleError):
    """Месяц не найден в файле"""

    pass


class InvalidDataError(ScheduleError):
    """Некорректные данные в файле"""

    pass


# Публичные функции для работы с дежурствами
def get_duties_for_current_date(division: str) -> str:
    """
    Получает дежурных на текущую дату

    Args:
        division: Подразделение

    Returns:
        Отформатированная строка с дежурными
    """
    parser = DutyScheduleParser()
    current_date = parser.get_current_yekaterinburg_date()
    duties = parser.get_duties_for_date(current_date, division)
    return parser.format_duties_for_date(current_date, duties)


def get_duties_for_date(date: datetime, division: str) -> str:
    """
    Получает дежурных на указанную дату

    Args:
        date: Дата
        division: Подразделение

    Returns:
        Отформатированная строка с дежурными
    """
    parser = DutyScheduleParser()
    duties = parser.get_duties_for_date(date, division)
    return parser.format_duties_for_date(date, duties)


def get_heads_for_current_date(division: str) -> str:
    """
    Получает руководителей групп на текущую дату

    Args:
        division: Подразделение

    Returns:
        Отформатированная строка с руководителями групп
    """
    parser = HeadScheduleParser()
    current_date = parser.get_current_yekaterinburg_date()
    heads = parser.get_heads_for_date(current_date, division)
    return parser.format_heads_for_date(current_date, heads)


def get_heads_for_date(date: datetime, division: str) -> str:
    """
    Получает руководителей групп на указанную дату

    Args:
        date: Дата
        division: Подразделение

    Returns:
        Отформатированная строка с руководителями групп
    """
    parser = HeadScheduleParser()
    heads = parser.get_heads_for_date(date, division)
    return parser.format_heads_for_date(date, heads)

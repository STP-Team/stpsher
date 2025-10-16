"""Модуль предоставляет базовые классы для всех парсеров с общей функциональностью.

Доступные классы:
- BaseParser: базовый абстрактный класс
- MonthlyScheduleParser: парсер для месячных графиков
- DutyParser: парсер для графиков дежурных
- BatchScheduleProcessor: обработчик пакетных операций.
"""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ...misc.helpers import short_name
from .cache import get_cache
from .excel import ExcelReader
from .file_managers import ScheduleFileManager

logger = logging.getLogger(__name__)


@dataclass
class ParsedScheduleEntry:
    """Представляет отдельную запись расписания.

    Attributes:
        day: День
        schedule: График
        work_hours: Рабочие часы
        additional_info: Дополнительная информация
    """

    day: str
    schedule: str
    work_hours: float = 0.0
    additional_info: Optional[str] = None


class BaseParser(ABC):
    """Базовый абстрактный класс для всех парсеров."""

    def __init__(self, uploads_folder: str = "uploads"):
        """Инициализация парсера с папкой uploads.

        Args:
            uploads_folder: Путь к папке загрузок
        """
        self.file_manager = ScheduleFileManager(uploads_folder)
        self.cache = get_cache()

    def get_reader(self, file_path: Path, sheet_name: str = "ГРАФИК") -> ExcelReader:
        """Получает ExcelReader для файла.

        Args:
            file_path: Путь к Excel файлу
            sheet_name: Название листа для чтения

        Returns:
            Экземпляр ExcelReader
        """
        return ExcelReader(file_path, sheet_name)

    @staticmethod
    def is_time_format(text: str) -> bool:
        """Проверяет есть ли в тексте время (в формате HH:MM-HH:MM).

        Args:
            text: Текст для проверки

        Returns:
            True если текст содержит указанный формат
        """
        if not text:
            return False
        time_pattern = r"\d{1,2}:\d{2}-\d{1,2}:\d{2}"
        return bool(re.search(time_pattern, text.strip()))

    @staticmethod
    def parse_time_range(time_str: str) -> Tuple[int, int]:
        """Разбор строки временного диапазона на начальные и конечные минуты.

        Args:
            time_str: Строка с диапазоном времени, например «09:00-18:00»

        Returns:
            Кортеж (start_minutes, end_minutes)
        """
        try:
            if "-" not in time_str:
                return 0, 0

            start_time, end_time = time_str.split("-")
            start_parts = start_time.strip().split(":")
            end_parts = end_time.strip().split(":")

            start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
            end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])

            # Работа в ночную смену
            if end_minutes < start_minutes:
                end_minutes += 24 * 60

            return start_minutes, end_minutes

        except (ValueError, IndexError):
            return 0, 0

    @staticmethod
    def calculate_work_hours(time_str: str) -> float:
        """Рассчитывает рабочие часы по временному диапазону.

        Args:
            time_str: Строка временного диапазона

        Returns:
            Кол-во рабочих часов
        """
        start_minutes, end_minutes = BaseParser.parse_time_range(time_str)

        if start_minutes == 0 and end_minutes == 0:
            return 0.0

        work_minutes = end_minutes - start_minutes

        # Вычесть 1 час на обед, если смена >= 8 часов
        work_hours = work_minutes / 60
        if work_hours >= 8:
            work_hours -= 1

        return round(work_hours, 1)

    @staticmethod
    def names_match(name1: str, name2: str) -> bool:
        """Проверяет, совпадают ли два имени (с учетом незначительных различий).

        Args:
            name1: Первые ФИО
            name2: Вторые ФИО

        Returns:
            True если имена совпадают
        """
        if not name1 or not name2:
            return False

        name1_clean = name1.strip()
        name2_clean = name2.strip()

        if name1_clean == name2_clean:
            return True

        parts1 = name1_clean.split()
        parts2 = name2_clean.split()

        # Сопоставление по фамилии и имени
        if len(parts1) >= 2 and len(parts2) >= 2:
            return parts1[0] == parts2[0] and parts1[1] == parts2[1]

        return False

    @staticmethod
    def is_valid_fullname(fullname_cell: str) -> bool:
        """Проверяет содержит ли ячейка валидные ФИО.

        Args:
            fullname_cell: Ячейка с ФИО для проверки

        Returns:
            True если ячейка содержит валидные ФИО, иначе False
        """
        return (
            len(fullname_cell.split()) >= 3
            and re.search(r"[А-Яа-я]", fullname_cell)
            and not re.search(r"\d", fullname_cell)
            and fullname_cell.strip() not in ["", "nan", "None"]
            and "переводы" not in fullname_cell.lower()
            and "увольнения" not in fullname_cell.lower()
        )

    @abstractmethod
    def parse(self, *args, **kwargs):
        """Метод parse для реализации подклассами."""
        pass


class MonthlyScheduleParser(BaseParser):
    """Парсер для операций с месячными графиками.

    Предоставляет функциональность для получения графиков на месяц
    с поддержкой пакетной обработки.
    """

    def get_user_schedule(
        self, fullname: str, month: str, division: str
    ) -> Dict[str, str]:
        """Извлекает график пользователя за месяц.

        Args:
            fullname: ФИО пользователя
            month: Название месяца
            division: Название направления

        Returns:
            Словарь с маппингом дня месяца и графика

        Raises:
            FileNotFoundError: Если файл графика не найден
        """
        try:
            schedule_file = self.file_manager.find_schedule_file(division)
            if not schedule_file:
                raise FileNotFoundError(f"График для направления {division} не найден")

            reader = self.get_reader(schedule_file)
            schedule = reader.extract_user_schedule(fullname, month)

            logger.info(
                f"[Excel] Найдено {len(schedule)} дней для {short_name(fullname)} в {month}"
            )
            return schedule

        except Exception as e:
            logger.error(f"[Excel] Ошибка получения графика: {e}")
            raise

    async def batch_get_schedules(
        self,
        users: List[Tuple[str, str, str]],  # [(fullname, month, division), ...]
    ) -> Dict[Tuple[str, str], Dict[str, str]]:
        """Пакетное получение графиков нескольких пользователей.

        Args:
            users: Список из (fullname, month, division)

        Returns:
            Словарь с маппингом (fullname, month) и словаря с графиком
        """
        results = {}

        # Группировка по файлам для минимизации чтения файлов
        by_file: Dict[str, List[Tuple[str, str]]] = {}

        for fullname, month, division in users:
            schedule_file = self.file_manager.find_schedule_file(division)
            if schedule_file:
                file_key = str(schedule_file)
                if file_key not in by_file:
                    by_file[file_key] = []
                by_file[file_key].append((fullname, month))

        # Обработать каждый файл один раз
        for file_path_str, user_list in by_file.items():
            file_path = Path(file_path_str)
            reader = self.get_reader(file_path)

            for fullname, month in user_list:
                try:
                    schedule = reader.extract_user_schedule(fullname, month)
                    results[(fullname, month)] = schedule
                except Exception as e:
                    logger.warning(
                        f"[Excel] Ошибка получения графика пакетом для {fullname}/{month}: {e}"
                    )
                    results[(fullname, month)] = {}

        logger.info(f"[Excel] Получено {len(results)} графиков пакетом")
        return results

    def parse(self, *args, **kwargs):
        """Реализация абстрактного метода parse."""
        return self.get_user_schedule(*args, **kwargs)


class DutyParser(BaseParser):
    """Парсер для графиков дежурных.

    Предоставляет утилиты для разбора записей дежурств
    и генерации названий листов.
    """

    @staticmethod
    def get_duty_sheet_name(date: datetime) -> str:
        """Генерирует название листа для графика дежурных.

        Args:
            date: Дата для проверки графика

        Returns:
            Название листа, например "Дежурство Январь"
        """
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

    @staticmethod
    def parse_duty_entry(cell_value: str) -> Tuple[str, str]:
        """Анализирует запись о дежурстве.

         Извлекает тип смены и время.

        Args:
            cell_value: Значение клетки, например "П 09:00-18:00" or "С 18:00-09:00"

        Returns:
            Кортеж (shift_type, schedule)
        """
        if not cell_value or cell_value.strip() in ["", "nan", "None"]:
            return "", ""

        cell_value = cell_value.strip()

        if cell_value.startswith("П "):
            return "П", cell_value[2:].strip()
        elif cell_value.startswith("С "):
            return "С", cell_value[2:].strip()
        else:
            if re.search(r"\d{1,2}:\d{2}-\d{1,2}:\d{2}", cell_value):
                return "", cell_value
            else:
                return "", cell_value

    def parse(self, *args, **kwargs):
        """Реализация абстрактного метода parse."""
        pass  # Duty parsing is more complex and kept in original parser


class BatchScheduleProcessor:
    """Обработчик для пакетных операций с графиками.

    Позволяет выполнять множественные операции с графиками параллельно.
    """

    def __init__(self, parser: BaseParser):
        """Инициализирует обработчик с экземпляром парсера.

        Args:
            parser: Экземпляр парсера для использования
        """
        self.parser = parser

    async def process_batch(
        self,
        operations: List[Tuple[str, Dict]],  # [(operation_name, kwargs), ...]
        max_concurrent: int = 10,
    ) -> List:
        """Обрабатывает множественные операции параллельно.

        Args:
            operations: Список кортежей (имя_операции, kwargs)
            max_concurrent: Максимум одновременных операций

        Returns:
            Список результатов
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def run_operation(op_name: str, kwargs: Dict):
            async with semaphore:
                try:
                    method = getattr(self.parser, op_name)
                    if asyncio.iscoroutinefunction(method):
                        return await method(**kwargs)
                    else:
                        return method(**kwargs)
                except Exception as e:
                    logger.error(f"Batch operation {op_name} failed: {e}")
                    return None

        tasks = [run_operation(op_name, kwargs) for op_name, kwargs in operations]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return results

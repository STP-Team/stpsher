"""Менеджер файлов расписаний.

Модуль предоставляет менеджеры для работы с файлами расписаний
и операциями с месяцами.
"""

import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ScheduleFileManager:
    """Менеджер для процессинга файлов с кешированием путей к файлам."""

    # Конфигурация кеша
    _CACHE_TTL = 300  # TTL кеша - 5 минут
    _cache: Dict[str, Tuple[Optional[Path], float]] = {}

    def __init__(self, uploads_folder: str = "uploads"):
        """Инициализирует менеджер с папкой uploads.

        Args:
            uploads_folder: Путь к папке загрузок
        """
        self.uploads_folder = Path(uploads_folder)

    def find_schedule_file(self, division: str) -> Optional[Path]:
        """Ищет файл графиков с использованием кеширования.

        Args:
            division: Направление пользователя

        Returns:
            Путь к файлу графиков или None если не найдено
        """
        # Сперва проверяем кеш
        current_time = time.time()
        if division in self._cache:
            cached_path, cached_time = self._cache[division]
            if current_time - cached_time < self._CACHE_TTL:
                # Проверяем существует ли файл до сих пор
                if cached_path and cached_path.exists():
                    logger.debug(
                        f"[График] Используем кешированный файл для {division}: {cached_path}"
                    )
                    return cached_path
                # Файл был удален, инвалидируем кеш
                del self._cache[division]

        # Файл не в кеше, или кеш истек - производим поиск
        result = self._search_schedule_file(division)

        # Кешируем результат
        self._cache[division] = (result, current_time)

        return result

    def _search_schedule_file(self, division: str) -> Optional[Path]:
        """Внутренний метод для поиска файла графиков без кеша.

        Args:
            division: Направление для поиска

        Returns:
            Путь к найденному файлу или None
        """
        try:
            all_files = []
            for root, dirs, files in os.walk(self.uploads_folder, followlinks=True):
                for name in files:
                    if name.startswith("ГРАФИК"):
                        all_files.append(Path(root) / name)

            filtered_files = []
            for file in all_files:
                name_parts = file.stem.split()
                logger.debug(
                    f"[График] Процессим файл: {file.name}, части названия: {name_parts}"
                )
                if len(name_parts) >= 3:
                    file_division = name_parts[1]
                    logger.debug(
                        f"[График] Направление файла: '{file_division}', ищем: '{division}'"
                    )
                    if file_division == division:
                        logger.debug(f"[График] СОВПАДЕНИЕ: {file.name}")
                        filtered_files.append(file)
                    else:
                        logger.debug(f"[График] НЕТ СОВПАДЕНИЯ: {file.name}")

            logger.debug(
                f"[График] Отфильтрованные файлы: {[f.name for f in filtered_files]}"
            )

            if filtered_files:
                latest_file = max(filtered_files, key=lambda f: f.stat().st_mtime)
                logger.debug(f"[График] Найден файл графиков: {latest_file}")
                return latest_file

            logger.error(f"[График] Файл графика для {division} не найден")
            return None

        except Exception as e:
            logger.error(f"[График] Ошибка нахождения файла: {e}")
            return None

    def clear_cache(self, division: Optional[str] = None) -> None:
        """Очищает кеш.

        Args:
            division: Направление для очистки кеша. Если не указано - очищает для всех направлений
        """
        if division:
            self._cache.pop(division, None)
            logger.debug(f"[График] Очищен кеш для направления: {division}")
        else:
            self._cache.clear()
            logger.debug("[График] Весь кеш очищен")


class MonthManager:
    """Менеджер для операций с месяцами.

    Предоставляет утилиты для нормализации названий месяцев
    и работы с порядком месяцев.
    """

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
        """Нормализирует название месяца.

        Args:
            month: Название месяца

        Returns:
            Нормализованное название месяца
        """
        return cls.MONTH_MAPPING.get(month.lower(), month.upper())

    @classmethod
    def get_available_months(cls) -> List[str]:
        """Получает список доступных месяцев.

        Returns:
            Список доступных месяцев
        """
        return [month.lower() for month in cls.MONTHS_ORDER]

    @classmethod
    def get_month_number(cls, month: str) -> int:
        """Получает номер месяца (1-12) из названия.

        Args:
            month: Название месяца

        Returns:
            Номер месяца
        """
        normalized_month = cls.normalize_month(month)
        try:
            return cls.MONTHS_ORDER.index(normalized_month) + 1
        except ValueError:
            return 1  # Стандартно на январь, если месяц не найден

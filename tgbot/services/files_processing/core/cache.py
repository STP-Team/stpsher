"""Высокопроизводительный слой кэширования для обработки Excel файлов.

Модуль предоставляет систему кэширования с автоматической инвалидацией
для оптимизации работы с Excel файлами.
"""

import hashlib
import logging
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class ExcelFileCache:
    """Система кэширования файлов Excel с автоматической инвалидацией."""

    def __init__(self, max_size: int = 10, ttl_seconds: int = 3600):
        """Инициализирует кэш с ограничениями по размеру и TTL.

        Args:
            max_size: Максимальное количество файлов для кэширования
            ttl_seconds: Время жизни записей в кэше в секундах
        """
        # Основной кэш для данных DataFrame
        self._df_cache: TTLCache = TTLCache(maxsize=max_size, ttl=ttl_seconds)

        # Кэш для метаданных файлов (время модификации, хэши)
        self._file_metadata: Dict[str, Dict[str, Any]] = {}

        # Готовые индексы для быстрого поиска
        self._user_indexes: Dict[
            str, Dict[str, int]
        ] = {}  # file_key -> {fullname: row_idx}
        self._date_indexes: Dict[
            str, Dict[Tuple[str, int], int]
        ] = {}  # file_key -> {(month, day): col_idx}

        logger.info(f"[Cache] Initialized with max_size={max_size}, ttl={ttl_seconds}s")

    def _get_file_key(self, file_path: Path) -> str:
        """Генерирует уникальный ключ кэша для файла.

        Args:
            file_path: Путь к файлу

        Returns:
            Строка с уникальным ключом кеша
        """
        return str(file_path.absolute())

    def _get_file_hash(self, file_path: Path) -> str:
        """Рассчитывает MD5 хеш файла для отслеживания изменений.

        Args:
            file_path: Путь к файлу

        Returns:
            MD5 хеш файла
        """
        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"[Cache] Ошибка при хешировании файла {file_path}: {e}")
            return ""

    def _is_file_modified(self, file_path: Path) -> bool:
        """Проверяет наличие изменений файла с момента последнего кеширования.

        Args:
            file_path: Путь к файлу

        Returns:
            True если файл был изменен, иначе False
        """
        file_key = self._get_file_key(file_path)

        if file_key not in self._file_metadata:
            return True

        try:
            current_mtime = file_path.stat().st_mtime
            cached_mtime = self._file_metadata[file_key].get("mtime", 0)

            if current_mtime != cached_mtime:
                logger.debug(f"[Cache] Файл изменен: {file_path.name}")
                return True

            return False

        except Exception as e:
            logger.warning(f"[Cache] Ошибка проверки модификации файлов: {e}")
            return True

    def get_dataframe(
        self, file_path: Path, sheet_name: str = "ГРАФИК"
    ) -> Optional[pd.DataFrame]:
        """Получает кешированный DataFrame или загружает из файла.

        Args:
            file_path: Путь к файлу Excel
            sheet_name: Название листа для чтения

        Returns:
            Pandas DataFrame или None если неудачно
        """
        file_key = self._get_file_key(file_path)
        cache_key = f"{file_key}:{sheet_name}"

        # Проверяем изменился ли файл
        if self._is_file_modified(file_path):
            logger.info(
                f"[Cache] Файл изменился, инвалидируем кеш для {file_path.name}"
            )
            self.invalidate(file_path)

        # Пытаемся получить файл из кеша
        if cache_key in self._df_cache:
            logger.debug(f"[Cache] Попадание для {file_path.name}:{sheet_name}")
            return self._df_cache[cache_key]

        # Загрузка из файла
        logger.info(f"[Cache] Промах для {file_path.name}:{sheet_name}, загрузка...")
        try:
            # Используем pandas
            df = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                header=None,
                dtype=str,
            )

            # Сохраняем в кеш
            self._df_cache[cache_key] = df

            # Обновляем метадату
            self._file_metadata[file_key] = {
                "mtime": file_path.stat().st_mtime,
                "hash": self._get_file_hash(file_path),
                "loaded_at": datetime.now(),
            }

            # Создаем индексы для быстрого поиска
            self._build_indexes(file_key, df)

            logger.info(
                f"[Cache] Кешировали {file_path.name}:{sheet_name} ({df.shape[0]}x{df.shape[1]})"
            )
            return df

        except Exception as e:
            # Проверяем если ошибка отсутствия листа
            error_msg = str(e).lower()
            is_worksheet_not_found = (
                ("worksheet" in error_msg and "not found" in error_msg)
                or ("sheet" in error_msg and "not found" in error_msg)
                or f"'{sheet_name.lower()}'" in error_msg
            )

            # Для графика дежурных ожидаемо не иметь графика для части месяцев
            if is_worksheet_not_found and "Дежурство" in sheet_name:
                logger.debug(
                    f"[Cache] Лист графика дежурных не найден (ожидаемо): {file_path.name}:{sheet_name}"
                )

            # Для графиков отмечаем предупреждением отсутствующий лист
            elif is_worksheet_not_found:
                logger.warning(f"[Cache] Лист не найден: {file_path.name}:{sheet_name}")

            # Для других ошибок (файл не найден, ошибка прав и т.д.), логируем ошибкой
            else:
                logger.error(
                    f"[Cache] Ошибка загрузки {file_path.name}:{sheet_name}: {e}"
                )

            return None

    def _build_indexes(self, file_key: str, df: pd.DataFrame):
        """Создает индексы для быстрого поиска пользователей и дат.

        Args:
            file_key: Уникальный ключ файла
            df: Pandas DataFrame
        """
        try:
            # Создает индекс пользователя (fullname -> row_idx)
            user_index = {}
            for row_idx in range(df.shape[0]):
                for col_idx in range(min(4, df.shape[1])):
                    cell_value = (
                        str(df.iloc[row_idx, col_idx])
                        if pd.notna(df.iloc[row_idx, col_idx])
                        else ""
                    )

                    if self._is_valid_fullname(cell_value.strip()):
                        fullname = cell_value.strip()
                        user_index[fullname] = row_idx
                        break

            self._user_indexes[file_key] = user_index
            logger.debug(f"[Cache] Built user index with {len(user_index)} entries")

            # Создает индекс дат (месяц, день) -> col_idx
            date_index = {}
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

            # Находит все столбцы месяца и их заголовки дней
            for col_idx in range(df.shape[1]):
                for row_idx in range(min(5, df.shape[0])):
                    cell_value = (
                        str(df.iloc[row_idx, col_idx])
                        if pd.notna(df.iloc[row_idx, col_idx])
                        else ""
                    )

                    # Проверяет наличие дневного паттерна, например "28Чт"
                    import re

                    day_match = re.search(
                        r"^(\d{1,2})[А-Яа-я]{0,2}$", cell_value.strip()
                    )
                    if day_match:
                        day = int(day_match.group(1))
                        # Находим какому месяцу принадлежит день
                        for month in months:
                            if self._column_belongs_to_month(df, col_idx, month):
                                date_index[(month, day)] = col_idx
                                break

            self._date_indexes[file_key] = date_index
            logger.debug(f"[Cache] Построили индекс дат с {len(date_index)} записями")

        except Exception as e:
            logger.warning(f"[Cache] Ошибка построения индекса дат: {e}")

    @staticmethod
    def _is_valid_fullname(text: str) -> bool:
        """Проверяет содержит ли текст ФИО.

        Args:
            text: Текст для проверки

        Returns:
            True если найдено ФИО, иначе False
        """
        if not text or text.strip() in ["", "nan", "None", "ДАТА →"]:
            return False

        words = text.split()
        if len(words) < 2:
            return False

        import re

        if not re.search(r"[А-Яа-я]", text):
            return False

        if re.search(r"\d", text):
            return False

        if text.upper() in ["СТАЖЕРЫ ОБЩЕГО РЯДА", "ДАТА"]:
            return False

        return True

    @staticmethod
    def _column_belongs_to_month(df: pd.DataFrame, col_idx: int, month: str) -> bool:
        """Проверяет принадлежит ли столбец указанному месяцу.

        Args:
            df: DataFrame для проверки
            col_idx: Индекс столбца
            month: Название месяца

        Returns:
            True если столбец принадлежит месяцу, иначе False
        """
        # Check column headers and nearby cells for month name
        for row_idx in range(min(3, df.shape[0])):
            for check_col in range(max(0, col_idx - 5), min(df.shape[1], col_idx + 1)):
                cell_value = (
                    str(df.iloc[row_idx, check_col])
                    if pd.notna(df.iloc[row_idx, check_col])
                    else ""
                )
                if month in cell_value.upper():
                    return True
        return False

    def get_user_row(self, file_path: Path, fullname: str) -> Optional[int]:
        """Быстрый поиск строки пользователя с использованием предварительно созданного индекса.

        Args:
            file_path: Путь к Excel файлу
            fullname: ФИО пользователя

        Returns:
            Индекс строки или None если не найдено
        """
        file_key = self._get_file_key(file_path)

        if file_key not in self._user_indexes:
            # Trigger cache load to build indexes
            self.get_dataframe(file_path)

        user_index = self._user_indexes.get(file_key, {})
        return user_index.get(fullname)

    def get_date_column(self, file_path: Path, month: str, day: int) -> Optional[int]:
        """Быстрый поиск столбца даты с использованием предварительно созданного индекса.

        Args:
            file_path: Путь к Excel файлу
            month: Название месяца на русском (например, "ЯНВАРЬ")
            day: Номер дня (1-31)

        Returns:
            Индекс столбца или None если не найдено
        """
        file_key = self._get_file_key(file_path)

        if file_key not in self._date_indexes:
            # Trigger cache load to build indexes
            self.get_dataframe(file_path)

        date_index = self._date_indexes.get(file_key, {})
        return date_index.get((month.upper(), day))

    def invalidate(self, file_path: Path):
        """Инвалидирует кэш для конкретного файла.

        Args:
            file_path: Путь к файлу для инвалидации
        """
        file_key = self._get_file_key(file_path)

        # Remove from all caches
        keys_to_remove = [k for k in self._df_cache.keys() if k.startswith(file_key)]
        for key in keys_to_remove:
            del self._df_cache[key]

        if file_key in self._file_metadata:
            del self._file_metadata[file_key]

        if file_key in self._user_indexes:
            del self._user_indexes[file_key]

        if file_key in self._date_indexes:
            del self._date_indexes[file_key]

        logger.info(f"[Cache] Invalidated cache for {file_path.name}")

    def clear(self):
        """Очищает все кэши."""
        self._df_cache.clear()
        self._file_metadata.clear()
        self._user_indexes.clear()
        self._date_indexes.clear()
        logger.info("[Cache] Cleared all caches")

    def get_stats(self) -> Dict[str, Any]:
        """Получает статистику кэша.

        Returns:
            Словарь со статистикой кэша
        """
        return {
            "cached_files": len(self._file_metadata),
            "cached_dataframes": len(self._df_cache),
            "indexed_users": sum(len(idx) for idx in self._user_indexes.values()),
            "indexed_dates": sum(len(idx) for idx in self._date_indexes.values()),
        }


# Global cache instance
_global_cache: Optional[ExcelFileCache] = None


def get_cache() -> ExcelFileCache:
    """Получает глобальный экземпляр кэша (паттерн singleton).

    Returns:
        Глобальный экземпляр ExcelFileCache
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = ExcelFileCache(max_size=20, ttl_seconds=3600)
    return _global_cache


@lru_cache(maxsize=128)
def normalize_month(month: str) -> str:
    """Нормализует название месяца с кэшированием.

    Args:
        month: Название месяца в любом формате

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
    return month_mapping.get(month.lower(), month.upper())

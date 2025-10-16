"""Пакет сервисов расписаний - Полностью оптимизирован с системой кэширования.

Все парсеры используют ExcelReader с интеллектуальным кэшированием для максимальной производительности:
- ScheduleParser: Месячные графики с O(1) поиском
- DutyScheduleParser: Графики дежурных с кэшированием на уровне месяца
- HeadScheduleParser: Графики руководителей с кэшированием
- GroupScheduleParser: Групповые графики с пакетной обработкой
- ExcelReader: Высокопроизводительное чтение Excel
- ExcelFileCache: Интеллектуальный слой кэширования с TTL и индексами
"""

# Core components
# Analyzers
from .analyzers import ScheduleAnalyzer

# Base classes
from .base_parsers import (
    BaseParser,
    BatchScheduleProcessor,
    MonthlyScheduleParser,
)

# Optimized caching components
from .cache import ExcelFileCache, get_cache
from .excel import ExcelReader
from .exceptions import (
    InvalidDataError,
    MonthNotFoundError,
    ScheduleError,
    ScheduleFileNotFoundError,
    UserNotFoundError,
)
from .file_managers import MonthManager, ScheduleFileManager
from .formatters import ScheduleFormatter
from .models import (
    DayInfo,
    DutyInfo,
    GroupMemberInfo,
    HeadInfo,
    ScheduleStats,
)

# Optimized parsers (fully refactored with caching)
from .parsers import (
    DutyScheduleParser,
    GroupScheduleParser,
    HeadScheduleParser,
    ScheduleParser,
)

__all__ = [
    # Optimized Parsers (USE THESE)
    "ScheduleParser",
    "DutyScheduleParser",
    "HeadScheduleParser",
    "GroupScheduleParser",
    # Core utilities
    "ScheduleFormatter",
    "ScheduleAnalyzer",
    "ScheduleFileManager",
    "MonthManager",
    # Models
    "DayInfo",
    "DutyInfo",
    "HeadInfo",
    "GroupMemberInfo",
    "ScheduleStats",
    # Exceptions
    "ScheduleError",
    "ScheduleFileNotFoundError",
    "UserNotFoundError",
    "MonthNotFoundError",
    "InvalidDataError",
    # Caching Components
    "ExcelFileCache",
    "get_cache",
    "ExcelReader",
    # Base classes
    "BaseParser",
    "MonthlyScheduleParser",
    "BatchScheduleProcessor",
]

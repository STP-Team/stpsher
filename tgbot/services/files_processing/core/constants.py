"""Centralized constants for files_processing module.

This module provides all shared constants used across the files_processing package,
including month mappings, validation patterns, and schedule type patterns.
"""

from typing import Dict, List

# Month name mappings (English -> Russian)
MONTH_NAMES_EN_TO_RU: Dict[str, str] = {
    "january": "январь",
    "february": "февраль",
    "march": "март",
    "april": "апрель",
    "may": "май",
    "june": "июнь",
    "july": "июль",
    "august": "август",
    "september": "сентябрь",
    "october": "октябрь",
    "november": "ноябрь",
    "december": "декабрь",
}

# Month normalization (any format -> uppercase Russian)
MONTH_MAPPING: Dict[str, str] = {
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

# Month order for iteration
MONTHS_ORDER: List[str] = [
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

# Month names for duty sheets (Title case)
MONTH_NAMES_TITLE: List[str] = [
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

# Invalid name patterns for fullname validation
INVALID_FULLNAME_PATTERNS: List[str] = [
    "СТАЖЕРЫ ОБЩЕГО РЯДА",
    "ДАТА",
    "ПЕРЕВОДЫ/УВОЛЬНЕНИЯ",
]

# Invalid text values for cell validation
INVALID_TEXT_VALUES: List[str] = ["", "nan", "None", "ДАТА →"]

# Schedule type patterns for day off detection
DAY_OFF_PATTERNS: List[str] = [
    "выходной",
    "0",
    "0.0",
    "",
]

# File type patterns
SCHEDULE_PATTERNS: List[str] = ["ГРАФИК * I*", "ГРАФИК * II*"]
DUTIES_PATTERNS: List[str] = ["Старшинство*", "*Старшинство*", "*старшинство*"]
STUDIES_PATTERNS: List[str] = ["Обучения *", "*обучения*"]

# Time pattern regex
TIME_PATTERN: str = r"\d{1,2}:\d{2}-\d{1,2}:\d{2}"

# Day header pattern (e.g., "28Чт")
DAY_HEADER_PATTERN: str = r"^(\d{1,2})[А-Яа-я]{0,2}$"

# Month number mapping (month name -> number 1-12)
MONTH_TO_NUMBER: Dict[str, int] = {
    "январь": 1,
    "февраль": 2,
    "март": 3,
    "апрель": 4,
    "май": 5,
    "июнь": 6,
    "июль": 7,
    "август": 8,
    "сентябрь": 9,
    "октябрь": 10,
    "ноябрь": 11,
    "декабрь": 12,
    "ЯНВАРЬ": 1,
    "ФЕВРАЛЬ": 2,
    "МАРТ": 3,
    "АПРЕЛЬ": 4,
    "МАЙ": 5,
    "ИЮНЬ": 6,
    "ИЮЛЬ": 7,
    "АВГУСТ": 8,
    "СЕНТЯБРЬ": 9,
    "ОКТЯБРЬ": 10,
    "НОЯБРЬ": 11,
    "ДЕКАБРЬ": 12,
}

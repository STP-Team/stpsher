"""Shared validation utilities.

This module provides common validation functions used across the files_processing package.
Centralized from: cache.py, excel.py, base.py, files.py, schedule.py, studies.py
"""

import re

from ..core.constants import INVALID_FULLNAME_PATTERNS, INVALID_TEXT_VALUES


def is_valid_fullname(text: str) -> bool:
    """Check if text contains valid Russian fullname.

    A valid fullname must:
    - Not be empty or contain invalid values
    - Have at least 2 words (surname + name)
    - Contain Cyrillic characters
    - Not contain digits
    - Not match invalid patterns

    Args:
        text: Text to validate as fullname

    Returns:
        True if text contains valid fullname, otherwise False

    Examples:
        >>> is_valid_fullname("Иванов Иван Иванович")
        True
        >>> is_valid_fullname(" Иванов")
        False
        >>> is_valid_fullname("СТАЖЕРЫ ОБЩЕГО РЯДА")
        False
    """
    if not text or text.strip() in INVALID_TEXT_VALUES:
        return False

    text = text.strip()
    words = text.split()

    # Must have at least 2 words (surname + name)
    if len(words) < 2:
        return False

    # Must contain Cyrillic characters
    if not re.search(r"[А-Яа-я]", text):
        return False

    # Must not contain digits
    if re.search(r"\d", text):
        return False

    # Must not match invalid patterns
    if text.upper() in INVALID_FULLNAME_PATTERNS:
        return False

    # Check for transfer/discharge related keywords
    if "переводы" in text.lower() or "увольнения" in text.lower():
        return False

    return True


def is_valid_person_name(text: str) -> bool:
    """Check if text contains valid person name (slightly relaxed version).

    Similar to is_valid_fullname but with additional checks for edge cases.

    Args:
        text: Text to validate as person name

    Returns:
        True if text contains valid person name, otherwise False
    """
    if not text or text.strip() in INVALID_TEXT_VALUES:
        return False

    text = text.strip()
    words = text.split()

    # Must have at least 2 words
    if len(words) < 2:
        return False

    # Must contain Cyrillic characters
    if not re.search(r"[А-Яа-я]", text):
        return False

    # Must not contain digits
    if re.search(r"\d", text):
        return False

    # Skip technical rows
    upper_text = text.upper()
    if upper_text in INVALID_FULLNAME_PATTERNS:
        return False

    return True


def normalize_schedule_value(value: str) -> str:
    """Normalize schedule value for comparison.

    Args:
        value: Schedule value to normalize

    Returns:
        Normalized value or empty string for invalid values
    """
    if not value or value.strip().lower() in ["", "nan", "none", "не указано", "0"]:
        return ""

    return value.strip()

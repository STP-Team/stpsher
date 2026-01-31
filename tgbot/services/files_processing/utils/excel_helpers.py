"""Excel operation helpers.

This module provides utility functions for working with pandas DataFrames
and Excel files. Replaces 20+ instances of duplicate cell access patterns.
"""

import logging
from typing import Any, List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def get_cell_value(df: pd.DataFrame, row: int, col: int, default: str = "") -> str:
    """Safely extract cell value from DataFrame.

    This replaces the common pattern:
        str(df.iloc[row, col]) if pd.notna(df.iloc[row, col]) else ""

    Args:
        df: Pandas DataFrame to read from
        row: Row index
        col: Column index
        default: Default value to return if cell is empty or out of bounds

    Returns:
        Cell value as string, or default value if extraction fails

    Examples:
        >>> df = pd.DataFrame([["a", "b"], ["c", "d"]])
        >>> get_cell_value(df, 0, 0)
        'a'
        >>> get_cell_value(df, 5, 0)  # Out of bounds
        ''
    """
    try:
        if row < df.shape[0] and col < df.shape[1]:
            value = df.iloc[row, col]
            return str(value) if pd.notna(value) else default
        return default
    except (IndexError, TypeError):
        return default


def batch_get_cells(
    df: pd.DataFrame, positions: List[Tuple[int, int]], default: str = ""
) -> List[str]:
    """Batch extract multiple cells efficiently.

    Args:
        df: Pandas DataFrame to read from
        positions: List of (row, col) tuples
        default: Default value for failed extractions

    Returns:
        List of cell values in same order as positions
    """
    return [get_cell_value(df, row, col, default) for row, col in positions]


def get_column_values(
    df: pd.DataFrame, col_idx: int, start_row: int = 0, end_row: int = None
) -> List[str]:
    """Get entire column values efficiently.

    Args:
        df: Pandas DataFrame to read from
        col_idx: Column index
        start_row: Starting row (default: 0)
        end_row: Ending row (default: last row)

    Returns:
        List of cell values from the column
    """
    if end_row is None:
        end_row = df.shape[0]

    try:
        column_data = df.iloc[start_row:end_row, col_idx].tolist()
        return [str(val) if pd.notna(val) else "" for val in column_data]
    except Exception as e:
        logger.error(f"Error getting column {col_idx}: {e}")
        return []


def get_row_values(
    df: pd.DataFrame, row_idx: int, start_col: int = 0, end_col: int = None
) -> List[str]:
    """Get entire row values efficiently.

    Args:
        df: Pandas DataFrame to read from
        row_idx: Row index
        start_col: Starting column (default: 0)
        end_col: Ending column (default: last column)

    Returns:
        List of cell values from the row
    """
    if end_col is None:
        end_col = df.shape[1]

    try:
        row_data = df.iloc[row_idx, start_col:end_col].tolist()
        return [str(val) if pd.notna(val) else "" for val in row_data]
    except Exception as e:
        logger.error(f"Error getting row {row_idx}: {e}")
        return []


def safe_int_cast(value: Any, default: int = 0) -> int:
    """Safely cast value to int.

    Args:
        value: Value to cast
        default: Default value if casting fails

    Returns:
        Integer value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

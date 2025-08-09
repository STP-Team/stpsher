"""
Utility functions for schedule operations.
"""

import logging
from typing import Dict, Optional

from .managers import ScheduleFileManager
from .models import ScheduleType

logger = logging.getLogger(__name__)


class ScheduleUtils:
    """Utilities for schedule operations"""

    @staticmethod
    def get_short_name(fullname: str) -> str:
        """Shorten full name to Last F.M."""
        parts = fullname.strip().split()
        if len(parts) >= 3:
            return f"{parts[0]} {parts[1][0]}.{parts[2][0]}."
        elif len(parts) == 2:
            return f"{parts[0]} {parts[1][0]}."
        return fullname

    @staticmethod
    def validate_division(division: str) -> bool:
        """Validate division name"""
        return "НТП" in division.upper() or "НЦК" in division.upper()

    @staticmethod
    def get_file_info(
        division: str, schedule_type: ScheduleType = ScheduleType.REGULAR
    ) -> Optional[Dict[str, any]]:
        """Get schedule file information"""
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
            logger.error(f"Error getting file info: {e}")
            return None

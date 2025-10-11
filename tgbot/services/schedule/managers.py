import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class ScheduleFileManager:
    """Manager for schedule file operations"""

    def __init__(self, uploads_folder: str = "uploads"):
        self.uploads_folder = Path(uploads_folder)

    def find_schedule_file(self, division: str) -> Optional[Path]:
        """Find schedule file by division (follows symlinked folders)"""
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
                    f"[График] Processing file: {file.name}, parts: {name_parts}"
                )
                if len(name_parts) >= 3:
                    file_division = name_parts[1]
                    logger.debug(
                        f"[График] File division: '{file_division}', looking for: '{division}'"
                    )
                    if file_division == division:
                        logger.debug(f"[График] MATCH: {file.name}")
                        filtered_files.append(file)
                    else:
                        logger.debug(f"[График] NO MATCH: {file.name}")

            logger.debug(f"[График] Filtered files: {[f.name for f in filtered_files]}")

            if filtered_files:
                latest_file = max(filtered_files, key=lambda f: f.stat().st_mtime)
                logger.debug(f"[График] Найден файл графиков: {latest_file}")
                return latest_file

            logger.error(f"[График] Файл графика для {division} не найден")
            return None

        except Exception as e:
            logger.error(f"Error finding schedule file: {e}")
            return None


class MonthManager:
    """Manager for month operations"""

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
        """Normalize month name"""
        return cls.MONTH_MAPPING.get(month.lower(), month.upper())

    @classmethod
    def get_available_months(cls) -> List[str]:
        """Get list of available months"""
        return [month.lower() for month in cls.MONTHS_ORDER]

    @classmethod
    def get_month_number(cls, month: str) -> int:
        """Get month number (1-12) from month name"""
        normalized_month = cls.normalize_month(month)
        try:
            return cls.MONTHS_ORDER.index(normalized_month) + 1
        except ValueError:
            return 1  # Default to January if month not found

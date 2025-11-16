"""Studies files_processing parser for processing and displaying training exchanges."""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
from pandas import DataFrame

from .base import BaseParser

logger = logging.getLogger(__name__)


class StudySession:
    """Represents a single study session."""

    def __init__(
        self,
        date: datetime,
        time: str,
        duration: str,
        title: str,
        experience_level: str,
        trainer: str,
        participants: List[
            Tuple[str, str, str, str, str]
        ],  # площадка, фио, рг, присутствие, причина
    ):
        self.date = date
        self.time = time
        self.duration = duration
        self.title = title
        self.experience_level = experience_level
        self.trainer = trainer
        self.participants = participants

    def __repr__(self):
        return f"<StudySession {self.date.strftime('%d.%m.%Y')} {self.time} '{self.title}'>"


class StudiesScheduleParser(BaseParser):
    """Парсер для обучений."""

    def __init__(self, uploads_folder: str = "uploads"):
        """Инициализация парсера для файла графиков обучений."""
        super().__init__(uploads_folder)

    def parse(self, *args, **kwargs):
        """Реализация абстрактного метода парсинга."""
        pass

    def parse_studies_file(self, file_path: Path) -> List[StudySession]:
        """Parse studies Excel file and return list of study sessions."""
        try:
            df = pd.read_excel(file_path, header=None)
            if df is None or df.empty:
                logger.warning(f"Empty or invalid studies file: {file_path}")
                return []

            sessions = []
            current_session = None
            participants = []

            i = 0
            while i < len(df):
                row = df.iloc[i]

                # Check if this row starts a new session (has datetime in first column)
                if pd.notna(row.iloc[0]) and isinstance(row.iloc[0], datetime):
                    # Save previous session if exists
                    if current_session:
                        current_session.participants = participants.copy()
                        sessions.append(current_session)
                        participants = []

                    # Parse new session header
                    date = row.iloc[0]
                    time = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
                    duration = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ""

                    # Get session details from next rows
                    title, experience_level, trainer = self._parse_session_details(
                        df, i + 1
                    )

                    current_session = StudySession(
                        date=date,
                        time=time,
                        duration=duration,
                        title=title,
                        experience_level=experience_level,
                        trainer=trainer,
                        participants=[],
                    )

                    # Skip to participant list (after header row "Площадка ФИО РГ...")
                    i = self._find_participants_start(df, i + 1)
                    continue

                # Check if this is a participant row
                elif current_session and self._is_participant_row(row):
                    participant = self._parse_participant_row(row)
                    if participant:
                        participants.append(participant)

                i += 1

            # Add final session
            if current_session:
                current_session.participants = participants.copy()
                sessions.append(current_session)

            logger.debug(f"Parsed {len(sessions)} study sessions from {file_path}")
            return sessions

        except Exception as e:
            logger.error(
                f"[Обучения] Ошибка парсинга обучений из файла {file_path}: {e}"
            )
            return []

    @staticmethod
    def _parse_session_details(df: DataFrame, start_row: int) -> Tuple[str, str, str]:
        """Parse session title, experience level, and trainer from rows after date."""
        title = ""
        experience_level = ""
        trainer = ""

        # Look at next few rows for session details
        for i in range(start_row, min(start_row + 10, len(df))):
            if i >= len(df):
                break

            row = df.iloc[i]
            first_col = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""

            # Title is usually in quotes
            if title == "" and '"' in first_col:
                title = first_col.strip('"')

            # Experience level contains "Стаж"
            elif "Стаж" in first_col or "стаж" in first_col:
                experience_level = first_col

            # Trainer row usually starts with "Тренер"
            elif first_col.startswith("Тренер") and row.index.size > 1:
                trainer_col = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
                trainer = trainer_col

        return title, experience_level, trainer

    @staticmethod
    def _find_participants_start(df: DataFrame, start_row: int) -> int:
        """Find the row where participant list starts (after header row)."""
        # Look for the header row with "Площадка", "ФИО", "РГ", etc.
        for i in range(start_row, min(start_row + 10, len(df))):
            if i >= len(df):
                break

            row = df.iloc[i]
            row_text = " ".join(str(cell) for cell in row if pd.notna(cell))

            # Check if this looks like participant header
            if any(
                keyword in row_text
                for keyword in ["Площадка", "ФИО", "РГ", "Присутствие"]
            ):
                return i + 1  # Return next row (first participant)

        return start_row + 5  # Default fallback

    @staticmethod
    def _is_participant_row(row) -> bool:
        """Check if row contains participant data."""
        first_col = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""

        # Should not be empty or contain datetime
        if not first_col or isinstance(row.iloc[0], datetime):
            return False

        # Should not contain quotes (session title) or "Стаж" or "Тренер"
        if any(
            keyword in first_col
            for keyword in ['"', "Стаж", "стаж", "Тренер", "Площадка"]
        ):
            return False

        # Should have some content in multiple columns
        non_empty_cols = sum(1 for cell in row if pd.notna(cell) and str(cell).strip())
        return non_empty_cols >= 2

    @staticmethod
    def _parse_participant_row(row) -> Optional[Tuple[str, str, str, str, str]]:
        """Parse participant data from row."""
        try:
            # Extract data from columns
            area = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
            name = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
            rg = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ""
            attendance = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ""
            reason = (
                str(row.iloc[4]) if row.index.size > 4 and pd.notna(row.iloc[4]) else ""
            )

            # Basic validation
            if not area or not name:
                return None

            # Skip header-like rows
            if any(keyword in name for keyword in ["ФИО", "Присутствие", "nan"]):
                return None

            return area, name, rg, attendance, reason

        except Exception as e:
            logger.debug(f"Error parsing participant row: {e}")
            return None

    def get_studies_for_date(
        self, date: datetime, file_name: str = "Обучения.xlsx"
    ) -> List[StudySession]:
        """Get all study sessions for specific date."""
        try:
            file_path = self.file_manager.uploads_folder / file_name
            if not file_path.exists():
                logger.warning(f"Файл обучений не найден: {file_path}")
                return []

            all_sessions = self.parse_studies_file(file_path)

            # Filter by date
            target_date = date.date()
            filtered_sessions = [
                session
                for session in all_sessions
                if session.date.date() == target_date
            ]

            logger.info(
                f"Found {len(filtered_sessions)} study sessions for {date.strftime('%d.%m.%Y')}"
            )
            return filtered_sessions

        except Exception as e:
            logger.error(f"Error getting studies for date {date}: {e}")
            return []

    def get_studies_for_user(
        self, user_fullname: str, file_name: str = "Обучения.xlsx"
    ) -> List[StudySession]:
        """Get all study sessions where specific user participates."""
        try:
            file_path = self.file_manager.uploads_folder / file_name
            if not file_path.exists():
                logger.warning(f"Файл обучений не найден: {file_path}")
                return []

            all_sessions = self.parse_studies_file(file_path)

            # Filter sessions where user participates
            user_sessions = []
            for session in all_sessions:
                for area, name, rg, attendance, reason in session.participants:
                    if self.names_match(user_fullname, name):
                        user_sessions.append(session)
                        break

            logger.info(
                f"Found {len(user_sessions)} study sessions for user {user_fullname}"
            )
            return user_sessions

        except Exception as e:
            logger.error(f"Error getting studies for user {user_fullname}: {e}")
            return []

    def format_studies_schedule(
        self, sessions: List[StudySession], title: str = "📚 Обучения"
    ) -> str:
        """Format study sessions for display."""
        from ..formatters import StudiesFormatter

        return StudiesFormatter.format_studies_schedule(sessions, title)

    def format_user_studies_schedule(
        self, sessions: List[StudySession], user_fullname: str
    ) -> str:
        """Format study sessions for specific user."""
        from ..formatters import StudiesFormatter

        return StudiesFormatter.format_user_studies_schedule(
            sessions, user_fullname, self.names_match
        )

    def format_studies_detailed(self, sessions: List[StudySession]) -> str:
        """Format study sessions with detailed participant information."""
        from ..formatters import StudiesFormatter

        return StudiesFormatter.format_studies_detailed(sessions)

    def format_schedule(self, data: List, date: datetime) -> str:
        """Format files_processing data for display - required by BaseExcelParser."""
        # For studies parser, this method formats study sessions
        if isinstance(data, list) and data and isinstance(data[0], StudySession):
            return self.format_studies_schedule(
                data, f"📚 Обучения • {date.strftime('%d.%m.%Y')}"
            )
        return f"📚 Обучения • {date.strftime('%d.%m.%Y')}\n\n❌ Нет данных для отображения"

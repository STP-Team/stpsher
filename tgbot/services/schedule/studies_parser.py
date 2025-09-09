"""
Studies schedule parser for processing and displaying training schedules.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
from pandas import DataFrame

from .parsers import BaseExcelParser

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


class StudiesScheduleParser(BaseExcelParser):
    """Parser for studies/training schedules."""

    def __init__(self, uploads_folder: str = "uploads"):
        super().__init__(uploads_folder)

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

    def _parse_session_details(
        self, df: DataFrame, start_row: int
    ) -> Tuple[str, str, str]:
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

    def _find_participants_start(self, df: DataFrame, start_row: int) -> int:
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

    def _is_participant_row(self, row) -> bool:
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

    def _parse_participant_row(self, row) -> Optional[Tuple[str, str, str, str, str]]:
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

            return (area, name, rg, attendance, reason)

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
                logger.warning(f"Studies file not found: {file_path}")
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
                logger.warning(f"Studies file not found: {file_path}")
                return []

            all_sessions = self.parse_studies_file(file_path)

            # Filter sessions where user participates
            user_sessions = []
            for session in all_sessions:
                for area, name, rg, attendance, reason in session.participants:
                    if self.utils.names_match(user_fullname, name):
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
        if not sessions:
            return f"<b>{title}</b>\n\n❌ Не найдено обучений"

        lines = [f"<b>{title}</b>\n"]

        # Group sessions by date
        sessions_by_date = {}
        for session in sessions:
            date_key = session.date.strftime("%d.%m.%Y")
            if date_key not in sessions_by_date:
                sessions_by_date[date_key] = []
            sessions_by_date[date_key].append(session)

        # Sort dates
        sorted_dates = sorted(
            sessions_by_date.keys(), key=lambda x: datetime.strptime(x, "%d.%m.%Y")
        )

        for date_str in sorted_dates:
            date_sessions = sessions_by_date[date_str]
            lines.append(f"📅 <b>{date_str}</b>\n")

            for session in date_sessions:
                lines.append(f"⏰ <b>{session.time}</b> ({session.duration})")
                lines.append(f"📖 {session.title}")

                if session.experience_level:
                    lines.append(f"👥 {session.experience_level}")

                if session.trainer:
                    lines.append(f"🎓 Тренер: {session.trainer}")

                # Show participant count
                if session.participants:
                    present_count = sum(
                        1
                        for _, _, _, attendance, _ in session.participants
                        if attendance == "+"
                    )
                    total_count = len(session.participants)
                    lines.append(f"👤 Участников: {present_count}/{total_count}")

                lines.append("")

        # Remove last empty line
        if lines and lines[-1] == "":
            lines.pop()

        return "\n".join(lines)

    def format_user_studies_schedule(
        self, sessions: List[StudySession], user_fullname: str
    ) -> str:
        """Format study sessions for specific user."""
        if not sessions:
            return "<b>📚 Твои обучения</b>\n\n❌ Не найдено обучений"

        lines = ["<b>📚 Твои обучения</b>\n"]

        # Sort by date
        sorted_sessions = sorted(sessions, key=lambda x: x.date)

        for session in sorted_sessions:
            lines.append(f"📅 <b>{session.date.strftime('%d.%m.%Y')}</b>")
            lines.append(f"⏰ {session.time} ({session.duration})")
            lines.append(f"📖 {session.title}")

            if session.experience_level:
                lines.append(f"👥 {session.experience_level}")

            if session.trainer:
                lines.append(f"🎓 Тренер: {session.trainer}")

            # Show user's attendance status
            for area, name, rg, attendance, reason in session.participants:
                if self.utils.names_match(user_fullname, name):
                    status_icon = (
                        "✅"
                        if attendance == "+"
                        else "❌"
                        if attendance == "-"
                        else "❓"
                    )
                    lines.append(f"{status_icon} Статус: {attendance}")
                    if reason:
                        lines.append(f"📝 Причина: {reason}")
                    break

            lines.append("")

        # Remove last empty line
        if lines and lines[-1] == "":
            lines.pop()

        return "\n".join(lines)

    def format_studies_detailed(self, sessions: List[StudySession]) -> str:
        """Format study sessions with detailed participant information."""
        if not sessions:
            return "<b>📚 Детальное расписание обучений</b>\n\n❌ Не найдено обучений"

        lines = ["<b>📚 Детальное расписание обучений</b>\n"]

        for session in sorted(sessions, key=lambda x: x.date):
            lines.append(f"📅 <b>{session.date.strftime('%d.%m.%Y')}</b>")
            lines.append(f"⏰ {session.time} ({session.duration})")
            lines.append(f"📖 {session.title}")

            if session.experience_level:
                lines.append(f"👥 {session.experience_level}")

            if session.trainer:
                lines.append(f"🎓 Тренер: {session.trainer}")

            lines.append("")
            lines.append("<b>👥 Участники:</b>")

            if session.participants:
                for area, name, rg, attendance, reason in session.participants:
                    status_icon = (
                        "✅"
                        if attendance == "+"
                        else "❌"
                        if attendance == "-"
                        else "❓"
                    )
                    participant_line = (
                        f"{status_icon} {self.utils.short_name(name)} ({area})"
                    )
                    if rg:
                        participant_line += f" - РГ: {rg}"
                    if reason:
                        participant_line += f" - {reason}"
                    lines.append(participant_line)
            else:
                lines.append("• Список участников пуст")

            lines.append("")

        # Remove last empty line
        if lines and lines[-1] == "":
            lines.pop()

        return "\n".join(lines)

    def format_schedule(self, data: List, date: datetime) -> str:
        """Format schedule data for display - required by BaseExcelParser."""
        # For studies parser, this method formats study sessions
        if isinstance(data, list) and data and isinstance(data[0], StudySession):
            return self.format_studies_schedule(
                data, f"📚 Обучения • {date.strftime('%d.%m.%Y')}"
            )
        return f"📚 Обучения • {date.strftime('%d.%m.%Y')}\n\n❌ Нет данных для отображения"

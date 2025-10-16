"""Утилиты для процессинга загруженных файлов."""

import fnmatch
import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd

from tgbot.misc.helpers import format_fullname
from tgbot.services.files_processing.parsers.base import BaseParser
from tgbot.services.schedulers.hr import get_fired_users_from_excel

logger = logging.getLogger(__name__)

# Паттерны типов файлов
SCHEDULE_PATTERNS = ["ГРАФИК * I*", "ГРАФИК * II*"]
DUTIES_PATTERNS = ["Старшинство*", "*Старшинство*", "*старшинство*"]
STUDIES_PATTERNS = ["Обучения *", "*обучения*"]


def find_header_columns(df: pd.DataFrame) -> Optional[dict]:
    """Находит строки заголовков в датафрейме.

    Args:
        df: Датафрейм для поиска

    Returns:
        Словарь со строками и колонками с полезными данными, или None если не найдено
    """
    for row_idx in range(min(10, len(df))):
        row_values = []
        for col_idx in range(min(10, len(df.columns))):
            cell_value = (
                str(df.iloc[row_idx, col_idx])
                if pd.notna(df.iloc[row_idx, col_idx])
                else ""
            )
            row_values.append(cell_value.strip().upper())

        position_col = head_col = None

        for col_idx, value in enumerate(row_values):
            if "ДОЛЖНОСТЬ" in value:
                position_col = col_idx
            if "РУКОВОДИТЕЛЬ" in value:
                head_col = col_idx

        if position_col is not None and head_col is not None:
            return {
                "header_row": row_idx,
                "fullname_col": 0,
                "position_col": position_col,
                "head_col": head_col,
            }

    return None


class FileTypeDetector:
    """Определяет тип файла используя паттерны названий файлов."""

    @staticmethod
    def is_schedule_file(file_name: str) -> bool:
        """Проверка является ли файл графиком сотрудников."""
        return any(fnmatch.fnmatch(file_name, pattern) for pattern in SCHEDULE_PATTERNS)

    @staticmethod
    def is_studies_file(file_name: str) -> bool:
        """Проверка является ли файл обучениями."""
        return any(fnmatch.fnmatch(file_name, pattern) for pattern in STUDIES_PATTERNS)

    @staticmethod
    def is_duties_file(file_name: str) -> bool:
        """Проверка является ли файл графиком дежурных."""
        return any(fnmatch.fnmatch(file_name, pattern) for pattern in DUTIES_PATTERNS)

    @staticmethod
    def get_file_type_display(file_name: str) -> str:
        """Получаем название типа файла для отображения."""
        if FileTypeDetector.is_schedule_file(file_name):
            return "📅 График"
        elif FileTypeDetector.is_duties_file(file_name):
            return "⚔️ Старшинство"
        elif FileTypeDetector.is_studies_file(file_name):
            return "📚 Обучения"
        else:
            return "📄 Обычный файл"


class FileStatsExtractor:
    """Достает статистику из загруженного файла."""

    @staticmethod
    def extract_stats(file_path: Path) -> dict:
        """Достает статистику из единичного Excel файла.

        Args:
            file_path: Путь к Excel файлу

        Returns:
            Словарь со статистикой: всего сотрудников, сотрудников с графиков, уволенных сотрудников
        """
        stats = {"total_people": 0, "schedule_people": 0, "fired_people": 0}

        try:
            # Проверяем является ли файл графиком
            original_name = file_path.name
            if file_path.name.startswith("temp_old_"):
                original_name = file_path.name.replace("temp_old_", "")

            if not FileTypeDetector.is_schedule_file(original_name):
                return stats

            # Читаем Excel файл
            df = pd.read_excel(file_path, sheet_name=0, header=None, dtype=str)

            # Считаем сотрудников
            stats["total_people"] = FileStatsExtractor._count_users_in_dataframe(df)
            stats["schedule_people"] = FileStatsExtractor._count_users_with_schedule(df)

            # Считаем уволенных сотрудников (только для обычных файлов, кроме временных)
            if not file_path.name.startswith("temp_old_"):
                fired_users = get_fired_users_from_excel([str(file_path)])
                stats["fired_people"] = len(fired_users)

        except Exception as e:
            logger.error(
                f"[Статистика файла] Ошибка проверки статистики файла {file_path}: {e}"
            )

        return stats

    @staticmethod
    def _count_users_in_dataframe(df: pd.DataFrame) -> int:
        """Считает пользователей в датафрейме.

        Args:
            df: Датафрейм

        Returns:
            Кол-во найденных пользователей в датафрейме
        """
        users_found = set()

        # Находим строку заголовков и колонки
        header_info = find_header_columns(df)
        if not header_info:
            return 0

        # Достаем пользователей
        for row_idx in range(header_info["header_row"] + 1, len(df)):
            fullname_cell = (
                str(df.iloc[row_idx, header_info["fullname_col"]])
                if pd.notna(df.iloc[row_idx, header_info["fullname_col"]])
                else ""
            )

            if BaseParser.is_valid_fullname(fullname_cell):
                users_found.add(fullname_cell.strip())

        return len(users_found)

    @staticmethod
    def _count_users_with_schedule(df: pd.DataFrame) -> int:
        """Считает пользователей с графиком.

        Args:
            df: Датафрейм

        Returns:
            Кол-во сотрудников с графиком в датафрейме
        """
        schedule_count = 0

        for row_idx in range(len(df)):
            for col_idx in range(min(4, len(df.columns))):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )
                if FileStatsExtractor._is_valid_person_name(cell_value.strip()):
                    # Проверяем есть ли график у пользователя в его строке
                    has_schedule = False
                    for schedule_col in range(4, min(len(df.columns), 50)):
                        if schedule_col < len(df.columns):
                            schedule_val = (
                                str(df.iloc[row_idx, schedule_col])
                                if pd.notna(df.iloc[row_idx, schedule_col])
                                else ""
                            )
                            if schedule_val.strip() and schedule_val.strip() not in [
                                "",
                                "nan",
                                "None",
                            ]:
                                has_schedule = True
                                break
                    if has_schedule:
                        schedule_count += 1
                    break

        return schedule_count

    @staticmethod
    def _is_valid_person_name(text: str) -> bool:
        """Проверяет содержит ли текст валидные ФИО.

        Args:
            text: Текст для проверки

        Returns:
            True если текст содержит ФИО, иначе False
        """
        if not text or text.strip() in ["", "nan", "None", "ДАТА →"]:
            return False

        text = text.strip()
        words = text.split()

        # Должен содержать минимум 2 слова (фамилия + имя)
        if len(words) < 2:
            return False

        # Должен содержать кириллические символы
        if not re.search(r"[А-Яа-я]", text):
            return False

        # Не должен содержать цифры
        if re.search(r"\d", text):
            return False

        # Пропускаем технические строки
        if text.upper() in ["СТАЖЕРЫ ОБЩЕГО РЯДА", "ДАТА", "ПЕРЕВОДЫ/УВОЛЬНЕНИЯ"]:
            return False

        return True


class FileProcessor:
    """Основной процессор файлов.

    Координирует все задачи процессинга.
    """

    @staticmethod
    async def process_schedule_file(
        file_path: Path, old_file_path: Optional[Path] = None
    ) -> dict:
        """Проверяет файл графиков и возвращает статистику.

        Args:
            file_path: Путь к новому файлу
            old_file_path: Опциональный путь к старому файлу для сравнения

        Returns:
            Словарь с результатами проверки и статистикой
        """
        results = {
            "new_file_stats": FileStatsExtractor.extract_stats(file_path),
            "old_file_stats": (
                FileStatsExtractor.extract_stats(old_file_path)
                if old_file_path
                else None
            ),
            "fired_names": [],
            "updated_names": [],
            "new_names": [],
            "error": None,
        }

        try:
            # TODO Добавить обработку уволенных сотрудников
            # Процессинг уволенных сотрудников
            pass

        except Exception as e:
            logger.error(f"Error processing schedule file: {e}")
            results["error"] = str(e)

        return results

    @staticmethod
    async def process_studies_file(file_path: Path) -> Optional[dict]:
        """Процессит файл обучений.

        Args:
            file_path: Путь к файлу обучений

        Returns:
            Словарь со статистикой обучений или None если файл не с обучениями
        """
        if not FileTypeDetector.is_studies_file(file_path.name):
            return None

        try:
            from ..parsers import StudiesScheduleParser

            parser = StudiesScheduleParser()
            sessions = parser.parse_studies_file(file_path)

            # Считаем статистику
            total_sessions = len(sessions)
            total_participants = 0
            unique_participants = set()
            present_participants = 0

            for session in sessions:
                total_participants += len(session.participants)
                for _area, name, _rg, attendance, _reason in session.participants:
                    unique_participants.add(name)
                    if attendance == "+":
                        present_participants += 1

            return {
                "total_sessions": total_sessions,
                "total_participants": total_participants,
                "unique_participants": len(unique_participants),
                "present_participants": present_participants,
                "sessions": sessions,
            }

        except Exception as e:
            logger.error(f"Error processing studies file: {e}")
            return None


def generate_detailed_stats_text(
    new_stats: dict, old_stats: Optional[dict] = None
) -> str:
    """Генерирует детальную статистику для отображения.

    Args:
        new_stats: Статистика для нового файла
        old_stats: Статистика старого файла (опционально)

    Returns:
        Форматированный текст статистики файлов графиков
    """
    if not new_stats:
        return ""

    text = "\n\n📊 <b>Детальная статистика</b>\n"

    # Статистика нового файла
    text += "<blockquote><b>Новый файл:</b>\n"
    text += f"• Всего сотрудников: {new_stats.get('total_people', 0)}\n"
    text += f"• С графиком: {new_stats.get('schedule_people', 0)}\n"
    if new_stats.get("fired_people", 0) > 0:
        text += f"• К увольнению: {new_stats.get('fired_people', 0)}\n"

    # Статистика старого файла (если существует)
    if old_stats:
        text += "\n<b>Предыдущий файл:</b>\n"
        text += f"• Всего сотрудников: {old_stats.get('total_people', 0)}\n"
        text += f"• С графиком: {old_stats.get('schedule_people', 0)}\n"
        if old_stats.get("fired_people", 0) > 0:
            text += f"• К увольнению: {old_stats.get('fired_people', 0)}\n"

        # Показываем разницу
        total_diff = new_stats.get("total_people", 0) - old_stats.get("total_people", 0)
        schedule_diff = new_stats.get("schedule_people", 0) - old_stats.get(
            "schedule_people", 0
        )

        if total_diff != 0 or schedule_diff != 0:
            text += "\n📈 <b>Изменения:</b>\n"
            if total_diff > 0:
                text += f"• +{total_diff} сотрудников\n"
            elif total_diff < 0:
                text += f"• {total_diff} сотрудников\n"

            if schedule_diff > 0:
                text += f"• +{schedule_diff} с графиком\n"
            elif schedule_diff < 0:
                text += f"• {schedule_diff} с графиком\n"

    return text + "</blockquote>"


def generate_user_changes_text(fired: list, updated: list, new: list) -> str:
    """Генерирует текст с изменениями сотрудников (уволен, обновлен, новый).

    Args:
        fired: Список ФИО уволенных сотрудников
        updated: Список ФИО обновленных сотрудников
        new: Список ФИО новых сотрудников

    Returns:
        Форматированное сообщение со статистикой изменений сотрудников
    """
    text = "\n<b>📊 Статистика обработки</b>\n"

    sections = [
        ("🔥 Уволено", fired),
        ("✏️ Обновлено", updated),
        ("➕ Добавлено", new),
    ]

    has_changes = False
    for title, names in sections:
        if names:
            has_changes = True
            text += f"\n{title} ({len(names)}):\n"
            text += "\n".join(
                f"• {format_fullname(name)}" for name in names[:10]
            )  # Показывает первые 10
            if len(names) > 10:
                text += f"\n... и ещё {len(names) - 10}"
            text += "\n"

    if not has_changes:
        text += "Уволенных, обновленных или добавленных пользователей нет"

    return text


def generate_studies_stats_text(stats: dict) -> str:
    """Генерирует текст статистики для файла обучений.

    Args:
        stats: Словарь со статистикой обучений

    Returns:
        Форматированный текст статистики обучений
    """
    text = "\n\n📚 <b>Статистика обучений</b>\n"
    text += f"• Всего сессий обучения: {stats.get('total_sessions', 0)}\n"
    text += f"• Всего участников: {stats.get('total_participants', 0)}\n"
    text += f"• Уникальных участников: {stats.get('unique_participants', 0)}\n"
    text += f"• Присутствовавших: {stats.get('present_participants', 0)}\n"

    return text

"""
Main schedule parsers.
"""

import logging
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from pandas import DataFrame

from infrastructure.database.models import User
from infrastructure.database.repo.requests import RequestsRepo

from . import DutyInfo, HeadInfo
from .analyzers import ScheduleAnalyzer
from .formatters import ScheduleFormatter
from .managers import MonthManager, ScheduleFileManager
from .models import GroupMemberInfo

logger = logging.getLogger(__name__)


class ExcelParser:
    """Парсер excel файлов"""

    def __init__(self, file_manager: ScheduleFileManager):
        self.file_manager = file_manager

    @staticmethod
    def read_excel_file(file_path: Path) -> Optional[DataFrame]:
        """
        Парсит файл графика на DataFrame
        :param file_path: Путь до файла
        :return: Датафрейм графика
        """
        sheet_name = "ГРАФИК"

        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            logger.debug(f"Successfully read sheet: {sheet_name}")
            return df
        except Exception as e:
            logger.debug(f"Failed to read sheet '{sheet_name}': {e}")
            return None

    @staticmethod
    def find_month_columns(df: pd.DataFrame, month: str) -> Tuple[int, int]:
        """
        Найти начальную и конечную колонку указанного месяца.
        :param df: Датафрейм графика
        :param month: Название месяца (любой регистр, можно неполное)
        """
        month = MonthManager.normalize_month(month)

        def find_month_index(target_month: str, start_column: int = 0) -> Optional[int]:
            """Находит индекс колонки, где встречается указанный месяц."""
            for col_idx in range(start_column, len(df.columns)):
                # Проверка в заголовках
                col_name = (
                    str(df.columns[col_idx]).upper() if df.columns[col_idx] else ""
                )
                if target_month in col_name:
                    return col_idx

                # Проверка в первых строках
                for row_idx in range(min(5, len(df))):
                    val = df.iat[row_idx, col_idx]
                    if isinstance(val, str) and target_month in val.upper():
                        return col_idx
            return None

        # Находим стартовую колонку месяца
        start_column = find_month_index(month)
        if start_column is None:
            raise ValueError(f"Месяц {month} не найден в графике")

        # Находим конец месяца (это колонка перед следующим месяцем)
        end_column = len(df.columns) - 1
        for m in MonthManager.MONTHS_ORDER:
            if m != month:
                next_month_col = find_month_index(m, start_column + 1)
                if next_month_col is not None:
                    end_column = next_month_col - 1
                    break

        logger.debug(f"Месяц '{month}' найден в колонках {start_column}-{end_column}")
        return start_column, end_column

    @staticmethod
    def find_day_headers(
        df: pd.DataFrame, start_column: int, end_column: int
    ) -> Dict[int, str]:
        """
        Находим заголовки дней
        :param df: Датафрейм графика
        :param start_column: Начальная колонка месяца
        :param end_column: Конечная колонка месяца
        :return: Список день:график
        """
        day_headers = {}

        for row_idx in range(min(5, len(df))):
            for col_idx in range(start_column, end_column + 1):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )

                day_pattern = r"(\d{1,2})([А-Яа-я]{1,2})"
                match = re.search(day_pattern, cell_value)

                if match:
                    day_num = match.group(1)
                    day_name = match.group(2)
                    day_headers[col_idx] = f"{day_num} ({day_name})"
                elif (
                    cell_value.strip().isdigit() and 1 <= int(cell_value.strip()) <= 31
                ):
                    day_headers[col_idx] = cell_value.strip()

        logger.debug(f"Found {len(day_headers)} days in headers")
        return day_headers

    @staticmethod
    def find_user_row(df: pd.DataFrame, fullname: str) -> Optional[int]:
        """
        Поиск строки пользователя
        :param df: Датафрейм графика
        :param fullname: ФИО искомого пользователя
        :return: Номер строки пользователя
        """
        for row_idx in range(len(df)):
            for col_idx in range(min(3, len(df.columns))):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )

                if fullname in cell_value:
                    logger.debug(f"Пользователь '{fullname}' найден в строке {row_idx}")
                    return row_idx

        return None


class ScheduleParser:
    """Main schedule parser class"""

    def __init__(self, uploads_folder: str = "uploads"):
        self.file_manager = ScheduleFileManager(uploads_folder)
        self.excel_parser = ExcelParser(self.file_manager)
        self.analyzer = ScheduleAnalyzer()
        self.formatter = ScheduleFormatter()

    def get_user_schedule(
        self, fullname: str, month: str, division: str
    ) -> Dict[str, str]:
        """
        Получает график пользователя
        :param fullname: ФИО искомого пользователя
        :param month: Месяц для получения графика
        :param division: Направление искомого пользователя
        :return:
        """
        try:
            schedule_file = self.file_manager.find_schedule_file(division)
            if not schedule_file:
                raise FileNotFoundError(
                    f"[График специалистов] Файл графиков {division} не найден"
                )

            df = self.excel_parser.read_excel_file(schedule_file)
            start_column, end_column = self.excel_parser.find_month_columns(df, month)
            day_headers = self.excel_parser.find_day_headers(
                df, start_column, end_column
            )

            user_row_idx = self.excel_parser.find_user_row(df, fullname)
            if user_row_idx is None:
                raise ValueError(
                    f"[График специалистов] Специалист {fullname} не найден в графике"
                )

            schedule = {}
            for col_idx in range(start_column, end_column + 1):
                if col_idx in day_headers:
                    day = day_headers[col_idx]
                    schedule_value = (
                        str(df.iloc[user_row_idx, col_idx])
                        if pd.notna(df.iloc[user_row_idx, col_idx])
                        else ""
                    )

                    schedule_value = schedule_value.strip()
                    if schedule_value.lower() in ["nan", "none", ""]:
                        schedule_value = "Не указано"

                    schedule[day] = schedule_value

            logger.info(
                f"[График специалистов] {fullname} запросил график на {month}: найдено {len(schedule)} дней"
            )
            return schedule

        except Exception as e:
            logger.error(f"Error getting schedule: {e}")
            raise

    def get_user_schedule_formatted(
        self, fullname: str, month: str, division: str, compact: bool = False
    ) -> str:
        """Get formatted user schedule"""
        try:
            schedule_data = self.get_user_schedule(fullname, month, division)

            if not schedule_data:
                return f"❌ График для <b>{fullname}</b> на {month} не найден"

            (
                work_days,
                days_off,
                vacation_days,
                vacation_bs_days,
                army_days,
                sick_days,
                missing_days,
            ) = self.analyzer.analyze_schedule(schedule_data)

            if compact:
                return self.formatter.format_compact(
                    month,
                    work_days,
                    days_off,
                    vacation_days,
                    vacation_bs_days,
                    army_days,
                    sick_days,
                    missing_days,
                )
            else:
                return self.formatter.format_detailed(
                    month,
                    work_days,
                    days_off,
                    vacation_days,
                    vacation_bs_days,
                    army_days,
                    sick_days,
                    missing_days,
                )

        except Exception as e:
            logger.error(f"[График специалистов] Ошибка форматирования графика: {e}")
            return f"❌ <b>Ошибка проверки графика:</b>\n<code>{e}</code>"


class DutyScheduleParser:
    """
    Парсер расписания дежурных
    """

    def __init__(self, uploads_folder: str = "uploads"):
        self.file_manager = ScheduleFileManager(uploads_folder)
        self.excel_parser = ExcelParser(self.file_manager)

    @staticmethod
    def get_duty_sheet_name(date: datetime) -> str:
        """Генерирует название листа для получения актуального расписания"""
        month_names = [
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
        month_name = month_names[date.month - 1]
        return f"Дежурство {month_name}"

    @staticmethod
    def find_date_column(df: pd.DataFrame, target_date: datetime) -> Optional[int]:
        """
        Поиск колонки для проверяемой даты
        :param df:
        :param target_date: Проверяемая дата
        :return: Номер колонки
        """
        target_day = target_date.day

        for row_idx in range(min(3, len(df))):
            for col_idx in range(len(df.columns)):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )

                day_pattern = r"^(\d{1,2})[А-Яа-я]{1,2}$"
                match = re.search(day_pattern, cell_value.strip())

                if match and int(match.group(1)) == target_day:
                    logger.debug(
                        f"[График дежурных] Нашли колонку с датой {target_day}: {col_idx}"
                    )
                    return col_idx

        logger.warning(f"[График дежурных] Колонка для даты {target_day} не найдена")
        return None

    @staticmethod
    def parse_duty_entry(cell_value: str) -> Tuple[str, str]:
        """
        Парсинг записи о дежурстве, экстракт типа смены и ее времени
        :param cell_value: Значение клетки
        :return:
        """
        if not cell_value or cell_value.strip() in ["", "nan", "None"]:
            return "", ""

        cell_value = cell_value.strip()

        if cell_value.startswith("П "):
            return "П", cell_value[2:].strip()
        elif cell_value.startswith("С "):
            return "С", cell_value[2:].strip()
        else:
            if re.search(r"\d{1,2}:\d{2}-\d{1,2}:\d{2}", cell_value):
                return "", cell_value
            else:
                return "", cell_value

    async def get_duties_for_date(
        self, date: datetime, division: str, stp_repo: RequestsRepo
    ) -> List[DutyInfo]:
        """
        Получает список дежурных на проверяемую дату
        :param date: Дата проверки
        :param division: Направление проверки
        :param stp_repo:
        :return: Список дежурных на проверяемую дату
        """
        try:
            schedule_file = self.file_manager.find_schedule_file(division)
            if not schedule_file:
                raise FileNotFoundError(
                    f"[График дежурных] Файл дежурных {division} не найден"
                )

            sheet_name = self.get_duty_sheet_name(date)

            try:
                df = pd.read_excel(schedule_file, sheet_name=sheet_name, header=None)
            except Exception as e:
                logger.warning(
                    f"[График дежурных] Не удалось прочитать график: {e}. Пробуем альтернативное название листа"
                )
                english_months = {
                    1: "January",
                    2: "February",
                    3: "March",
                    4: "April",
                    5: "May",
                    6: "June",
                    7: "July",
                    8: "August",
                    9: "September",
                    10: "October",
                    11: "November",
                    12: "December",
                }
                alt_sheet_name = f"Дежурство {english_months[date.month]}"
                df = pd.read_excel(
                    schedule_file, sheet_name=alt_sheet_name, header=None
                )

            date_col = self.find_date_column(df, date)
            if date_col is None:
                logger.warning(
                    f"[График дежурных] Дата {date.day} не найдена в графике дежурных"
                )
                return []

            duties = []

            for row_idx in range(len(df)):
                name = ""
                for col_idx in range(min(3, len(df.columns))):
                    cell_value = (
                        str(df.iloc[row_idx, col_idx])
                        if pd.notna(df.iloc[row_idx, col_idx])
                        else ""
                    )

                    if (
                        len(cell_value.split()) >= 3
                        and re.search(r"[А-Яа-я]", cell_value)
                        and not re.search(r"\d", cell_value)
                    ):
                        name = cell_value.strip()
                        break

                if not name:
                    continue

                if date_col < len(df.columns):
                    duty_cell = (
                        str(df.iloc[row_idx, date_col])
                        if pd.notna(df.iloc[row_idx, date_col])
                        else ""
                    )

                    if duty_cell and duty_cell.strip() not in ["", "nan", "None"]:
                        shift_type, schedule = self.parse_duty_entry(duty_cell)

                        if shift_type in ["С", "П"] and re.search(
                            r"\d{1,2}:\d{2}-\d{1,2}:\d{2}", schedule
                        ):
                            user: User = await stp_repo.user.get_user(fullname=name)
                            if user:
                                duties.append(
                                    DutyInfo(
                                        name=name,
                                        user_id=user.user_id,
                                        username=user.username,
                                        schedule=schedule,
                                        shift_type=shift_type,
                                        work_hours=schedule,
                                    )
                                )

            logger.info(
                f"[График дежурных] Нашел {len(duties)} дежурных на дату {date.strftime('%d.%m.%Y')}"
            )
            return duties

        except Exception as e:
            logger.error(f"[График дежурных] Ошибка проверки дежурных: {e}")
            return []

    @staticmethod
    def get_gender_emoji(name: str) -> str:
        """
        Определение пола по имени
        :param name: Полные ФИО или отчество
        :return: Эмодзи с отображением пола
        """
        parts = name.split()
        if len(parts) >= 3:
            patronymic = parts[2]
            if patronymic.endswith("на"):
                return "👩‍🦰"
            elif patronymic.endswith(("ич", "ович", "евич")):
                return "👨"
        return "👨"

    @staticmethod
    def parse_time_range(time_str: str) -> Tuple[int, int]:
        """
        Парсит время начала и конца дежурки
        :param time_str:
        :return:
        """
        try:
            if "-" not in time_str:
                return 0, 0

            start_time, end_time = time_str.split("-")
            start_parts = start_time.strip().split(":")
            end_parts = end_time.strip().split(":")

            start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
            end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])

            if end_minutes < start_minutes:
                end_minutes += 24 * 60

            return start_minutes, end_minutes

        except (ValueError, IndexError):
            return 0, 0

    def format_duties_for_date(self, date: datetime, duties: List[DutyInfo]) -> str:
        """
        Форматирование списка руководителей для отображения в меню. Группировка по времени
        :param date: Дата проверки
        :param duties: Список дежурных на дату провреки
        :return: Форматированное сообщение для отправки пользователю
        """
        if not duties:
            return f"<b>👮‍♂️ Дежурные • {date.strftime('%d.%m.%Y')}</b>\n\n❌ Дежурных на эту дату не найдено"

        lines = [f"<b>👮‍♂️ Дежурные • {date.strftime('%d.%m.%Y')}</b>\n"]

        time_groups = {}
        for duty in duties:
            time_schedule = duty.schedule
            if not time_schedule or not re.search(
                r"\d{1,2}:\d{2}-\d{1,2}:\d{2}", time_schedule
            ):
                continue

            if time_schedule not in time_groups:
                time_groups[time_schedule] = {"duties": [], "helpers": []}

            if duty.shift_type == "С":
                time_groups[time_schedule]["duties"].append(duty)
            elif duty.shift_type == "П":
                time_groups[time_schedule]["helpers"].append(duty)
            else:
                time_groups[time_schedule]["duties"].append(duty)

        sorted_times = sorted(
            time_groups.keys(), key=lambda t: self.parse_time_range(t)[0]
        )

        for time_schedule in sorted_times:
            group = time_groups[time_schedule]

            lines.append(f"⏰ <b>{time_schedule}</b>")

            for duty in group["duties"]:
                gender_emoji = self.get_gender_emoji(duty.name)
                if duty.username:
                    lines.append(
                        f"{gender_emoji}Старший - <a href='t.me/{duty.username}'>{duty.name}</a>"
                    )
                else:
                    lines.append(
                        f"{gender_emoji}Старший - <a href='tg://user?id={duty.user_id}'>{duty.name}</a>"
                    )

            for duty in group["helpers"]:
                gender_emoji = self.get_gender_emoji(duty.name)
                if duty.username:
                    lines.append(
                        f"{gender_emoji}Помощник - <a href='t.me/{duty.username}'>{duty.name}</a>"
                    )
                else:
                    lines.append(
                        f"{gender_emoji}Помощник - <a href='tg://user?id={duty.user_id}'>{duty.name}</a>"
                    )

            lines.append("")

        if lines and lines[-1] == "":
            lines.pop()

        return "\n".join(lines)


class HeadScheduleParser:
    """
    Парсер расписания руководителей
    """

    def __init__(self, uploads_folder: str = "uploads"):
        self.file_manager = ScheduleFileManager(uploads_folder)
        self.excel_parser = ExcelParser(self.file_manager)
        self.formatter = ScheduleFormatter()

    @staticmethod
    def find_date_column(df: pd.DataFrame, target_date: datetime) -> Optional[int]:
        """
        Поиск колонки для проверяемой даты
        :param df:
        :param target_date: Проверяемая дата
        :return: Номер колонки
        """
        target_day = target_date.day

        for row_idx in range(min(5, len(df))):
            for col_idx in range(len(df.columns)):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )

                day_pattern = r"^(\d{1,2})[А-Яа-я]{1,2}$"
                match = re.search(day_pattern, cell_value.strip())

                if match and int(match.group(1)) == target_day:
                    logger.debug(
                        f"[График РГ] Нашли колонку с датой {target_day}: {col_idx}"
                    )
                    return col_idx

        logger.warning(f"[График РГ] Колонка для даты {target_day} не найдена")
        return None

    async def get_heads_for_date(
        self, date: datetime, division: str, stp_repo: RequestsRepo
    ) -> List[HeadInfo]:
        """
        Получение списка руководителей на смене на день проверки
        :param date: Дата дня проверки
        :param division: Направление проверки
        :param stp_repo: Модель БД
        :return: Список руководителей, работающих в день проверки
        """
        duty_parser = DutyScheduleParser()
        duties = await duty_parser.get_duties_for_date(date, division, stp_repo)

        try:
            schedule_file = self.file_manager.find_schedule_file(division)
            if not schedule_file:
                raise FileNotFoundError(
                    f"[График РГ] Файл графиков {division} не найден"
                )

            df = pd.read_excel(schedule_file, sheet_name="ГРАФИК", header=None)

            date_col = self.find_date_column(df, date)
            if date_col is None:
                logger.warning(f"[График РГ] Дата {date.day} не найдена в графике")
                return []

            heads = []

            for row_idx in range(len(df)):
                position_found = False
                name = ""

                for col_idx in range(min(5, len(df.columns))):
                    cell_value = (
                        str(df.iloc[row_idx, col_idx])
                        if pd.notna(df.iloc[row_idx, col_idx])
                        else ""
                    )

                    if "Руководитель группы" in cell_value:
                        position_found = True

                    if (
                        not name
                        and len(cell_value.split()) >= 3
                        and re.search(r"[А-Яа-я]", cell_value)
                        and "Руководитель" not in cell_value
                    ):
                        name = cell_value.strip()

                if not position_found or not name:
                    continue
                if date_col < len(df.columns):
                    schedule_cell = (
                        str(df.iloc[row_idx, date_col])
                        if pd.notna(df.iloc[row_idx, date_col])
                        else ""
                    )

                    if schedule_cell and schedule_cell.strip() not in [
                        "",
                        "nan",
                        "None",
                    ]:
                        if re.search(r"\d{1,2}:\d{2}-\d{1,2}:\d{2}", schedule_cell):
                            duty_info = await self._check_duty_for_head(name, duties)
                            user: User = await stp_repo.user.get_user(fullname=name)
                            if user:
                                heads.append(
                                    HeadInfo(
                                        name=name,
                                        user_id=user.user_id,
                                        username=user.username,
                                        schedule=schedule_cell.strip(),
                                        duty_info=duty_info,
                                    )
                                )
                            else:
                                pass
            logger.info(
                f"[График РГ] Нашли {len(heads)} руководителей на дату {date.strftime('%d.%m.%Y')}"
            )
            return heads

        except Exception as e:
            logger.error(f"[График РГ] Ошибка проверки руководителей: {e}")
            return []

    async def _check_duty_for_head(
        self,
        head_name: str,
        duties: List[DutyInfo],
    ) -> Optional[str]:
        """
        Проверка является ли руководитель дежурным в проверяемый день
        :param duties:
        :param head_name: ФИО руководителя
        :return:
        """
        try:
            for duty in duties:
                if self._names_match(head_name, duty.name):
                    return f"{duty.schedule} [{duty.shift_type}]"

            return None

        except Exception as e:
            logger.debug(f"[График РГ] Ошибка проверки дежурности для {head_name}: {e}")
            return None

    @staticmethod
    def _names_match(name1: str, name2: str) -> bool:
        """Check if names match (considering writing differences)"""
        parts1 = name1.split()
        parts2 = name2.split()

        if len(parts1) >= 2 and len(parts2) >= 2:
            return parts1[0] == parts2[0] and parts1[1] == parts2[1]

        return False

    def format_heads_for_date(self, date: datetime, heads: List[HeadInfo]) -> str:
        """
        Форматирование списка руководителей для отображения в меню
        :param date: Дата проверяемого дня
        :param heads: Список руководителей на проверяемый день
        :return: Форматированное сообщение для отправки пользователю
        """
        if not heads:
            return f"<b>👑 Руководители групп • {date.strftime('%d.%m.%Y')}</b>\n\n❌ Руководители групп на эту дату не найдены"

        lines = [f"<b>👑 Руководители групп • {date.strftime('%d.%m.%Y')}</b>\n"]

        time_groups = {}
        for head in heads:
            time_schedule = head.schedule
            if not time_schedule or not re.search(
                r"\d{1,2}:\d{2}-\d{1,2}:\d{2}", time_schedule
            ):
                continue

            time_match = re.search(r"(\d{1,2}:\d{2}-\d{1,2}:\d{2})", time_schedule)
            time_key = time_match.group(1) if time_match else time_schedule

            if time_key not in time_groups:
                time_groups[time_key] = []
            time_groups[time_key].append(head)

        def parse_time_start(time_str: str) -> int:
            try:
                if "-" in time_str:
                    start_time = time_str.split("-")[0].strip()
                    hour, minute = start_time.split(":")
                    return int(hour) * 60 + int(minute)
                return 0
            except (ValueError, IndexError):
                return 0

        sorted_times = sorted(time_groups.keys(), key=parse_time_start)

        for time_schedule in sorted_times:
            group_heads: list[HeadInfo] = time_groups[time_schedule]

            lines.append(f"⏰ <b>{time_schedule}</b>")

            for head in group_heads:
                gender_emoji = self.formatter.get_gender_emoji(head.name)
                if head.username:
                    head_line = (
                        f"{gender_emoji} <a href='t.me/{head.username}'>{head.name}</a>"
                    )
                else:
                    head_line = f"{gender_emoji} <a href='tg://user?id={head.user_id}'>{head.name}</a>"

                if head.duty_info:
                    head_line += f" ({head.duty_info})"

                lines.append(head_line)

            lines.append("")

        if lines and lines[-1] == "":
            lines.pop()

        return "\n".join(lines)


class GroupScheduleParser:
    """
    Парсер группового расписания для руководителей и участников группы
    """

    def __init__(self, uploads_folder: str = "uploads"):
        self.file_manager = ScheduleFileManager(uploads_folder)
        self.excel_parser = ExcelParser(self.file_manager)
        self.formatter = ScheduleFormatter()

    @staticmethod
    def _extract_start_time(working_hours: str) -> str:
        """
        Извлекает время начала работы из строки рабочих часов
        :param working_hours: Строка типа "09:00-17:00" или "09:00-13:00 18:00-22:00"
        :return: Время начала работы, например "09:00"
        """
        if not working_hours or working_hours == "Не указано":
            return "Не указано"

        # Ищем первый паттерн времени
        time_pattern = r"(\d{1,2}:\d{2})"
        match = re.search(time_pattern, working_hours)

        if match:
            return match.group(1)

        return "Не указано"

    @staticmethod
    def _parse_time_for_sorting(time_str: str) -> Tuple[int, int]:
        """
        Парсит время для сортировки
        :param time_str: Строка времени типа "09:00"
        :return: (час, минута) для сортировки
        """
        if not time_str or time_str == "Не указано":
            return 99, 0  # Ставим "Не указано" в конец

        try:
            hour, minute = time_str.split(":")
            return int(hour), int(minute)
        except (ValueError, IndexError):
            return 99, 0

    def _group_members_by_start_time(
        self, members: List[GroupMemberInfo]
    ) -> Dict[str, List[GroupMemberInfo]]:
        """
        Группирует сотрудников по времени начала работы
        :param members: Список сотрудников
        :return: Словарь {время_начала: [сотрудники]}
        """
        grouped = defaultdict(list)

        for member in members:
            start_time = self._extract_start_time(member.working_hours)
            grouped[start_time].append(member)

        return dict(grouped)

    def _format_member_with_link(self, member: GroupMemberInfo) -> str:
        """
        Форматирует имя сотрудника с ссылкой и полными рабочими часами
        :param member: Информация о сотруднике
        :return: Отформатированная строка
        """
        display_name = self.short_name(member.name)

        # Создаем ссылку на пользователя
        if member.username:
            user_link = f"{self.get_gender_emoji(member.name)} <a href='t.me/{member.username}'>{display_name}</a>"
        elif member.user_id:
            user_link = f"{self.get_gender_emoji(member.name)} <a href='tg://user?id={member.user_id}'>{display_name}</a>"
        else:
            user_link = f"{self.get_gender_emoji(member.name)} {display_name}"

        # Добавляем полные рабочие часы в <code> тегах
        working_hours = member.working_hours or "Не указано"
        return f"{user_link} <code>{working_hours}</code>"

    def format_group_schedule_for_head(
        self,
        date: datetime,
        group_members: List[GroupMemberInfo],
        page: int = 1,
        members_per_page: int = 20,  # Увеличиваем размер страницы из-за нового компактного формата
    ) -> tuple[str, int, bool, bool]:
        """
        Форматирование группового расписания для руководителя с новым форматом группировки по времени начала
        """
        if not group_members:
            return (
                f"👥 <b>Группа на {date.strftime('%d.%m.%Y')}</b>\n\n❌ Сотрудники не найдены",
                1,
                False,
                False,
            )

        # Применяем пагинацию к полному списку сотрудников
        total_members = len(group_members)
        total_pages = max(1, (total_members + members_per_page - 1) // members_per_page)

        start_idx = (page - 1) * members_per_page
        end_idx = start_idx + members_per_page
        page_members = group_members[start_idx:end_idx]

        # Группируем сотрудников на текущей странице по времени начала
        grouped_by_start_time = self._group_members_by_start_time(page_members)

        # Сортируем группы по времени начала
        sorted_start_times = sorted(
            grouped_by_start_time.keys(), key=self._parse_time_for_sorting
        )

        # Формируем текст
        lines = [f"👥 <b>Ваша группа на {date.strftime('%d.%m.%Y')}</b>", ""]

        for start_time in sorted_start_times:
            members = grouped_by_start_time[start_time]

            # Проверяем, есть ли сотрудники с одинаковым временем начала, но разными полными часами
            unique_full_schedules = set(member.working_hours for member in members)

            if len(unique_full_schedules) == 1 and len(members) == 1:
                # Если один сотрудник с уникальным расписанием, показываем полное время в заголовке
                full_hours = members[0].working_hours or "Не указано"
                lines.append(f"🕒 <b>{full_hours}</b>")
                lines.append(
                    self._format_member_with_link(members[0]).replace(
                        f" <code>{full_hours}</code>", ""
                    )
                )
            else:
                # Если несколько сотрудников с одним временем начала, группируем по времени начала
                lines.append(f"🕒 <b>{start_time}</b>")
                for member in members:
                    lines.append(self._format_member_with_link(member))

            lines.append("")

        # Убираем последнюю пустую строку
        if lines and lines[-1] == "":
            lines.pop()

        # Добавляем информацию о пагинации
        if total_pages > 1:
            lines.append("")
            lines.append(
                f"📄 Страница {page}/{total_pages} (показано {len(page_members)} из {total_members} сотрудников)"
            )

        return ("\n".join(lines), total_pages, page > 1, page < total_pages)

    def format_group_schedule_for_user(
        self,
        date: datetime,
        group_members: List[GroupMemberInfo],
        user_name: str,
        head_name: str,
        page: int = 1,
        members_per_page: int = 20,
    ) -> tuple[str, int, bool, bool]:
        """
        Форматирование группового расписания для пользователя с новым форматом группировки по времени начала
        """
        if not group_members:
            return (
                f"👥 <b>Моя группа • {date.strftime('%d.%m.%Y')}</b>\n\n❌ Коллеги не найдены",
                1,
                False,
                False,
            )

        # Исключаем самого пользователя из списка
        colleagues = [
            member
            for member in group_members
            if not self._names_match(user_name, member.name)
        ]

        if not colleagues:
            return (
                f"👥 <b>Моя группа • {date.strftime('%d.%m.%Y')}</b>\n\n❌ Коллеги не найдены",
                1,
                False,
                False,
            )

        # Применяем пагинацию к списку коллег
        total_colleagues = len(colleagues)
        total_pages = max(
            1, (total_colleagues + members_per_page - 1) // members_per_page
        )

        start_idx = (page - 1) * members_per_page
        end_idx = start_idx + members_per_page
        page_colleagues = colleagues[start_idx:end_idx]

        # Группируем коллег на текущей странице по времени начала
        grouped_by_start_time = self._group_members_by_start_time(page_colleagues)

        # Сортируем группы по времени начала
        sorted_start_times = sorted(
            grouped_by_start_time.keys(), key=self._parse_time_for_sorting
        )

        # Формируем текст
        lines = [f"👥 <b>Моя группа • {date.strftime('%d.%m.%Y')}</b>", ""]

        for start_time in sorted_start_times:
            members = grouped_by_start_time[start_time]

            # Проверяем, есть ли коллеги с одинаковым временем начала, но разными полными часами
            unique_full_schedules = set(member.working_hours for member in members)

            if len(unique_full_schedules) == 1 and len(members) == 1:
                # Если один коллега с уникальным расписанием, показываем полное время в заголовке
                full_hours = members[0].working_hours or "Не указано"
                lines.append(f"🕒 <b>{full_hours}</b>")
                lines.append(
                    self._format_member_with_link(members[0]).replace(
                        f" <code>{full_hours}</code>", ""
                    )
                )
            else:
                # Если несколько коллег с одним временем начала, группируем по времени начала
                lines.append(f"🕒 <b>{start_time}</b>")
                for member in members:
                    lines.append(self._format_member_with_link(member))

            lines.append("")

        # Убираем последнюю пустую строку
        if lines and lines[-1] == "":
            lines.pop()

        # Добавляем информацию о пагинации
        if total_pages > 1:
            lines.append("")
            lines.append(
                f"📄 Страница {page}/{total_pages} (показано {len(page_colleagues)} из {total_colleagues} коллег)"
            )

        return ("\n".join(lines), total_pages, page > 1, page < total_pages)

    # Вспомогательные методы (остаются без изменений)
    @staticmethod
    def find_date_column(df: pd.DataFrame, target_date: datetime) -> Optional[int]:
        """
        Поиск колонки для проверяемой даты
        """
        target_day = target_date.day

        for row_idx in range(min(5, len(df))):
            for col_idx in range(len(df.columns)):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )

                if not cell_value:
                    continue

                if re.search(rf"\b{target_day}\b", cell_value):
                    return col_idx

        return None

    def _get_cell_value(self, df: pd.DataFrame, row: int, col: int) -> str:
        """Безопасное получение значения ячейки"""
        try:
            if row < len(df) and col < len(df.columns):
                value = df.iloc[row, col]
                return str(value) if pd.notna(value) else ""
            return ""
        except (IndexError, TypeError):
            return ""

    def _find_header_columns(self, df: pd.DataFrame) -> dict:
        """Поиск колонок в заголовке"""
        # Simplified implementation - you'll need to adapt based on your actual Excel structure
        return {
            "header_row": 0,
            "schedule_col": 1,
            "position_col": 4,
            "head_col": 5,
        }

    def _is_valid_name(self, name_cell: str) -> bool:
        """Проверка валидности имени"""
        if not name_cell or name_cell.strip() in ["", "nan", "None"]:
            return False
        parts = name_cell.strip().split()
        return len(parts) >= 2

    def _names_match(self, name1: str, name2: str) -> bool:
        """Проверка совпадения имен"""
        if not name1 or not name2:
            return False

        name1_clean = name1.strip()
        name2_clean = name2.strip()

        if name1_clean == name2_clean:
            return True

        parts1 = name1_clean.split()
        parts2 = name2_clean.split()

        if len(parts1) >= 2 and len(parts2) >= 2:
            return parts1[0] == parts2[0] and parts1[1] == parts2[1]

        return False

    def _is_time_format(self, text: str) -> bool:
        """Проверяет, является ли текст временным форматом"""
        if not text:
            return False
        time_pattern = r"\d{1,2}:\d{2}-\d{1,2}:\d{2}"
        return bool(re.search(time_pattern, text.strip()))

    def _sort_members_by_time(
        self, members: List[GroupMemberInfo]
    ) -> List[GroupMemberInfo]:
        """Сортирует участников группы по времени начала работы"""
        return sorted(
            members,
            key=lambda m: self._parse_time_for_sorting(
                self._extract_start_time(m.working_hours)
            ),
        )

    async def get_group_members_for_head(
        self, head_fullname: str, date: datetime, division: str, stp_repo
    ) -> List[GroupMemberInfo]:
        """Получение списка сотрудников группы для руководителя"""
        try:
            schedule_file = self.file_manager.find_schedule_file(division)
            if not schedule_file:
                raise FileNotFoundError(f"Файл расписания для {division} не найден")

            df = pd.read_excel(schedule_file, sheet_name=0, header=None)
            header_info = self._find_header_columns(df)
            if not header_info:
                logger.warning("Не найдены необходимые колонки в файле")
                return []

            date_column = self.find_date_column(df, date)
            group_members = []

            for row_idx in range(header_info["header_row"] + 1, len(df)):
                name_cell = self._get_cell_value(df, row_idx, 0)
                schedule_cell = self._get_cell_value(
                    df, row_idx, header_info.get("schedule_col", 1)
                )
                position_cell = self._get_cell_value(
                    df, row_idx, header_info.get("position_col", 4)
                )
                head_cell = self._get_cell_value(
                    df, row_idx, header_info.get("head_col", 5)
                )

                if not self._names_match(head_fullname, head_cell):
                    continue

                if not self._is_valid_name(name_cell):
                    continue

                working_hours = "Не указано"
                if date_column is not None:
                    hours_cell = self._get_cell_value(df, row_idx, date_column)
                    if hours_cell and self._is_time_format(hours_cell):
                        working_hours = hours_cell

                if working_hours == "Не указано":
                    for col_idx in range(
                        len(df.columns) - 1, max(header_info.get("head_col", 5), 0), -1
                    ):
                        cell_value = self._get_cell_value(df, row_idx, col_idx)
                        if self._is_time_format(cell_value):
                            working_hours = cell_value
                            break

                user = None
                try:
                    user = await stp_repo.user.get_user(fullname=name_cell.strip())
                except Exception as e:
                    logger.debug(f"Ошибка получения пользователя {name_cell}: {e}")

                if not user:
                    logger.debug(
                        f"Пользователь {name_cell.strip()} не найден в БД, пропускаем"
                    )
                    continue

                member = GroupMemberInfo(
                    name=name_cell.strip(),
                    user_id=user.user_id,
                    username=user.username,
                    schedule=schedule_cell.strip() if schedule_cell else "Не указано",
                    position=position_cell.strip() if position_cell else "Специалист",
                    working_hours=working_hours,
                )

                group_members.append(member)

            logger.info(
                f"Найдено {len(group_members)} сотрудников в группе {head_fullname}"
            )
            return self._sort_members_by_time(group_members)

        except Exception as e:
            logger.error(f"Ошибка получения группы для {head_fullname}: {e}")
            return []

    async def get_group_members_for_user(
        self, user_fullname: str, date: datetime, division: str, stp_repo
    ) -> List[GroupMemberInfo]:
        """Получение списка коллег по группе для обычного пользователя"""
        try:
            user = await stp_repo.user.get_user(fullname=user_fullname)
            if not user or not user.head:
                logger.warning(
                    f"Пользователь {user_fullname} не найден или не имеет руководителя"
                )
                return []

            all_members = await self.get_group_members_for_head(
                user.head, date, division, stp_repo
            )

            return self._sort_members_by_time(all_members)

        except Exception as e:
            logger.error(f"Ошибка получения коллег для {user_fullname}: {e}")
            return []

    @staticmethod
    def get_gender_emoji(name: str) -> str:
        """
        Определение пола по имени
        :param name: Полные ФИО или отчество
        :return: Эмодзи с отображением пола
        """
        parts = name.split()
        if len(parts) >= 3:
            patronymic = parts[2]
            if patronymic.endswith("на"):
                return "👩‍🦰"
            elif patronymic.endswith(("ич", "ович", "евич")):
                return "👨"
        return "👨"

    @staticmethod
    def short_name(full_name: str) -> str:
        # если есть скобки с датой — убираем
        clean_name = full_name.split("(")[0].strip()

        # разбиваем по пробелам
        parts = clean_name.split()

        if len(parts) >= 2:
            # первые два слова (Имя + Фамилия или Фамилия + Имя)
            return " ".join(parts[:2])
        else:
            return clean_name  # если только одно слово

"""
Duty schedule parser functionality.
"""

import logging
import re
from datetime import datetime
from typing import List, Optional, Tuple

import pandas as pd

from infrastructure.database.models import User
from infrastructure.database.repo.requests import RequestsRepo

from .excel_parser import ExcelParser
from .managers import ScheduleFileManager
from .models import DutyInfo

logger = logging.getLogger(__name__)


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
            except Exception:
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
                            user: User = await stp_repo.users.get_user(fullname=name)
                            if user:
                                duties.append(
                                    DutyInfo(
                                        name=name,
                                        user_id=user.user_id,
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
                lines.append(
                    f"{gender_emoji}Старший - <a href='tg://user?id={duty.user_id}'>{duty.name}</a>"
                )

            for duty in group["helpers"]:
                gender_emoji = self.get_gender_emoji(duty.name)
                lines.append(
                    f"{gender_emoji}Помощник - <a href='tg://user?id={duty.user_id}'>{duty.name}</a>"
                )

            lines.append("")

        if lines and lines[-1] == "":
            lines.pop()

        return "\n".join(lines)

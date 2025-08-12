"""
Head schedule parser functionality.
"""

import logging
import re
from datetime import datetime
from typing import List, Optional

import pandas as pd

from infrastructure.database.models import User
from infrastructure.database.repo.requests import RequestsRepo

from . import ScheduleFormatter
from .duty_parser import DutyScheduleParser
from .excel_parser import ExcelParser
from .managers import ScheduleFileManager
from .models import HeadInfo

logger = logging.getLogger(__name__)


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
                            duty_info = await self._check_duty_for_head(
                                name, date, division, stp_repo
                            )
                            user: User = await stp_repo.users.get_user(fullname=name)
                            if user:
                                heads.append(
                                    HeadInfo(
                                        name=name,
                                        user_id=user.user_id,
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
        self, head_name: str, date: datetime, division: str, stp_repo: RequestsRepo
    ) -> Optional[str]:
        """
        Проверка является ли руководитель дежурным в проверяемый день
        :param head_name: ФИО руководителя
        :param date: Дата проверки
        :param division: Направление для проверки
        :return:
        """
        try:
            duty_parser = DutyScheduleParser()
            duties = await duty_parser.get_duties_for_date(date, division, stp_repo)

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
                head_line = f"{gender_emoji} <a href='tg://user?id={head.user_id}'>{head.name}</a>"

                if head.duty_info:
                    head_line += f" ({head.duty_info})"

                lines.append(head_line)

            lines.append("")

        if lines and lines[-1] == "":
            lines.pop()

        return "\n".join(lines)

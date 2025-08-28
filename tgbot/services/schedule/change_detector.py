import logging
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from infrastructure.database.models import User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.services.broadcaster import send_message
from tgbot.services.schedule.parsers import ScheduleParser

logger = logging.getLogger(__name__)


class ScheduleChangeDetector:
    """Сервис обнаружения и уведомления об изменениях в графиках пользователей"""

    def __init__(self, uploads_folder: str = "uploads"):
        self.uploads_folder = Path(uploads_folder)
        self.schedule_parser = ScheduleParser(uploads_folder)

    async def process_schedule_changes(
        self, new_file_name: str, old_file_name: str, bot, stp_repo: RequestsRepo
    ) -> List[str]:
        """
        Процессинг изменений в графике между старым и новым графиками и отправка уведомлений.

        :param new_file_name: Название файла нового графика
        :param old_file_name: Название файла старого графика
        :param bot: Инстанс бота для отправки сообщений
        :param stp_repo: Репозиторий для операций с БД
        :return: Список ФИО пользователей для уведомления об изменениях
        """
        try:
            logger.info(
                f"[График] Проверяем изменения графика: {old_file_name} -> {new_file_name}"
            )

            # Get list of users affected by changes
            changed_users = await self._detect_schedule_changes(
                new_file_name, old_file_name
            )

            if not changed_users:
                logger.info("[График] Не найдено изменений в загруженном графике")
                return []

            # Отправка уведомления затронутым пользователям
            notified_users = []
            for user_changes in changed_users:
                user: User = await stp_repo.user.get_user(
                    fullname=user_changes["fullname"]
                )
                if user and user.user_id:
                    success = await self._send_change_notification(
                        bot=bot, user_id=user.user_id, user_changes=user_changes
                    )
                    if success:
                        notified_users.append(user_changes["fullname"])
                else:
                    logger.warning(
                        f"[График] {user_changes['fullname']} не найден в БД или не имеет user_id"
                    )

            logger.info(
                f"[График] Отправили {len(notified_users)} пользователям об изменениях в графике"
            )
            return notified_users

        except Exception as e:
            logger.error(f"[График] Ошибка проверки изменений в графике: {e}")
            return []

    async def _detect_schedule_changes(
        self, new_file_name: str, old_file_name: str
    ) -> List[Dict]:
        """
        Обнаружение изменений в графике между старым и новым файлами.

        :param new_file_name: Название файла нового графика
        :param old_file_name: Название файла старого графика
        :return: Список словарей, содержащий изменения в графике
        """
        try:
            old_file_path = self.uploads_folder / old_file_name
            new_file_path = self.uploads_folder / new_file_name

            if not old_file_path.exists():
                logger.warning(f"Old file {old_file_name} not found for comparison")
                return []

            if not new_file_path.exists():
                logger.warning(f"New file {new_file_name} not found")
                return []

            # Read both files
            old_schedules = self._extract_all_user_schedules(old_file_path)
            new_schedules = self._extract_all_user_schedules(new_file_path)

            # Compare schedules and detect changes
            changes = []
            for fullname in new_schedules:
                if fullname in old_schedules:
                    old_schedule = old_schedules[fullname]
                    new_schedule = new_schedules[fullname]

                    change_details = self._compare_user_schedules(
                        fullname, old_schedule, new_schedule
                    )

                    if change_details:
                        changes.append(change_details)

            return changes

        except Exception as e:
            logger.error(f"Error detecting schedule changes: {e}")
            return []

    def _extract_all_user_schedules(self, file_path: Path) -> Dict[str, Dict[str, str]]:
        """
        Экстракт графиков всех пользователей из Excel файла.

        :param file_path: Путь до Excel файла
        :return: Словарь с маппингом пользователя с его графиком
        """
        schedules = {}

        try:
            # Читаем файл
            df = pd.read_excel(file_path, sheet_name=0, header=None)

            # Находим заголовки
            day_headers = self._find_day_headers(df)
            if not day_headers:
                logger.warning(f"[График] Не найдены заголовки для {file_path}")
                return schedules

            # Экстрактим графики пользователей
            for row_idx in range(len(df)):
                # Ищем ФИО в первом столбце
                fullname = None
                for col_idx in range(min(4, len(df.columns))):
                    cell_value = (
                        str(df.iloc[row_idx, col_idx])
                        if pd.notna(df.iloc[row_idx, col_idx])
                        else ""
                    )
                    if self._is_valid_fullname(cell_value):
                        fullname = cell_value.strip()
                        break

                if fullname:
                    # Экстрактим график пользователя
                    user_schedule = {}
                    for day_col, day_name in day_headers.items():
                        if day_col < len(df.columns):
                            schedule_value = (
                                str(df.iloc[row_idx, day_col])
                                if pd.notna(df.iloc[row_idx, day_col])
                                else ""
                            )
                            user_schedule[day_name] = schedule_value.strip()

                    schedules[fullname] = user_schedule

            logger.debug(
                f"[График] Вытащили график для {len(schedules)} пользователей из {file_path}"
            )
            return schedules

        except Exception as e:
            logger.error(f"[График] Ошибка экстракта графиков из {file_path}: {e}")
            return schedules

    @staticmethod
    def _find_day_headers(df: pd.DataFrame) -> Dict[int, str]:
        """
        Находим хедеры дней в датафрейме

        :param df: Датафрейм
        :return:
        """
        day_headers = {}

        # Look for day headers in first few rows
        for row_idx in range(min(5, len(df))):
            for col_idx in range(len(df.columns)):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )

                # Check if it's a day number (1-31)
                if cell_value.strip().isdigit() and 1 <= int(cell_value.strip()) <= 31:
                    day_headers[col_idx] = f"День {cell_value.strip()}"
                # Check for patterns like "1 (пн)"
                elif cell_value and "(" in cell_value and ")" in cell_value:
                    day_headers[col_idx] = cell_value.strip()

        return day_headers

    def _is_valid_fullname(self, text: str) -> bool:
        """Check if text looks like a valid fullname."""
        if not text or text.strip() in ["", "nan", "None"]:
            return False

        text = text.strip()
        words = text.split()

        # Should have at least 2 words (surname + name)
        if len(words) < 2:
            return False

        # Should contain Cyrillic characters
        import re

        if not re.search(r"[А-Яа-я]", text):
            return False

        # Should not contain digits
        if re.search(r"\d", text):
            return False

        return True

    def _compare_user_schedules(
        self, fullname: str, old_schedule: Dict[str, str], new_schedule: Dict[str, str]
    ) -> Optional[Dict]:
        """
        Compare old and new schedules for a user and return change details.

        Args:
            fullname: User's full name
            old_schedule: Dictionary of old schedule data
            new_schedule: Dictionary of new schedule data

        Returns:
            Dictionary with change details or None if no changes
        """
        changes = []

        # Compare each day
        all_days = set(old_schedule.keys()) | set(new_schedule.keys())

        for day in all_days:
            old_value = old_schedule.get(day, "").strip()
            new_value = new_schedule.get(day, "").strip()

            # Normalize empty values
            old_value = (
                old_value
                if old_value and old_value.lower() not in ["nan", "none", ""]
                else ""
            )
            new_value = (
                new_value
                if new_value and new_value.lower() not in ["nan", "none", ""]
                else ""
            )

            if old_value != new_value:
                changes.append(
                    {
                        "day": day,
                        "old_value": old_value or "не назначено",
                        "new_value": new_value or "не назначено",
                    }
                )

        if changes:
            return {"fullname": fullname, "changes": changes}

        return None

    async def _send_change_notification(
        self, bot, user_id: int, user_changes: Dict
    ) -> bool:
        """
        Send notification to user about schedule changes.

        Args:
            bot: Bot instance
            user_id: Telegram user ID
            user_changes: Dictionary with user change information

        Returns:
            True if notification was sent successfully
        """
        try:
            fullname = user_changes["fullname"]
            changes = user_changes["changes"]

            # Create notification message
            message = "🔔 <b>Изменение в вашем графике</b>\n\n"
            message += f"Привет, {fullname.split()[0]}!\n\n"
            message += "В вашем графике произошли изменения:\n\n"

            for change in changes:
                day = change["day"]
                old_val = change["old_value"]
                new_val = change["new_value"]

                message += f"📅 <b>{day}</b>\n"
                message += f"   Было: {old_val}\n"
                message += f"   Стало: <b>{new_val}</b>\n\n"

            message += 'Пожалуйста, ознакомься с обновленным графиком в разделе "📅 Мой график".'

            # Send notification
            success = await send_message(
                bot=bot, user_id=user_id, text=message, disable_notification=False
            )

            if success:
                logger.info(
                    f"Schedule change notification sent to {fullname} (ID: {user_id})"
                )
            else:
                logger.warning(
                    f"Failed to send schedule change notification to {fullname} (ID: {user_id})"
                )

            return success

        except Exception as e:
            logger.error(f"Error sending change notification: {e}")
            return False

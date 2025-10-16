"""Сервис обнаружения и уведомления об изменениях в графиках пользователей."""

import logging
from pathlib import Path
from typing import Any, Dict, List

from stp_database import Employee, MainRequestsRepo

from tgbot.keyboards.schedule import changed_schedule_kb
from tgbot.misc.helpers import tz
from tgbot.services.broadcaster import send_message
from tgbot.services.files_processing.formatters.notifications import (
    ScheduleChangeFormatter,
)
from tgbot.services.files_processing.utils.schedule import (
    compare_schedules,
    extract_users_schedules,
)

logger = logging.getLogger(__name__)


class ScheduleChangeDetector:
    """Сервис обнаружения и уведомления об изменениях в графиках пользователей."""

    def __init__(self, uploads_folder: str = "uploads"):
        """Инициализация детектора изменений.

        Args:
            uploads_folder: Папка с загруженными файлами
        """
        self.uploads_folder = Path(uploads_folder)
        self.formatter = ScheduleChangeFormatter()

    async def process_schedule_changes(
        self, new_file_name: str, old_file_name: str, bot, stp_repo: MainRequestsRepo
    ) -> tuple[list[Any], list[str]]:
        """Процессинг изменений в графике между старым и новым графиками и отправка уведомлений.

        Args:
            new_file_name: Название нового файла графиков
            old_file_name: Название старого файла графиков
            bot: Экземпляр бота
            stp_repo: Репозиторий операций с базой STP

        Returns:
            Кортеж со списком сотрудников с измененным графиков, и уведомленных сотрудников
        """
        try:
            logger.info(
                f"[График] Проверяем изменения графика: {old_file_name} -> {new_file_name}"
            )

            # Проверяем наличие изменения в графиках
            changed_users = await self._detect_schedule_changes(
                new_file_name, old_file_name, stp_repo
            )

            if not changed_users:
                logger.info("[График] Не найдено изменений в загруженном графике")
                return [], []

            # Отправка уведомления затронутым пользователям
            notified_users = []
            for user_changes in changed_users:
                user: Employee = await stp_repo.employee.get_users(
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
            return changed_users, notified_users

        except Exception as e:
            logger.error(f"[График] Ошибка проверки изменений в графике: {e}")
            return [], []

    async def _detect_schedule_changes(
        self, new_file_name: str, old_file_name: str, stp_repo: MainRequestsRepo
    ) -> List[Dict]:
        """Обнаружение изменений в графике между старым и новым файлами.

        Читает каждый файл только один раз и извлекает полные расписания всех пользователей.

        Args:
            new_file_name: Название нового файла графиков
            old_file_name: Название старого файла графиков
            stp_repo: Репозиторий операций с базой STP

        Returns:
            Список словарей с изменениями в графике
        """
        try:
            old_file_path = self.uploads_folder / old_file_name
            new_file_path = self.uploads_folder / new_file_name

            if not old_file_path.exists():
                logger.warning(
                    f"[Графики] Старый файл {old_file_name} не найден для сравнения"
                )
                return []

            if not new_file_path.exists():
                logger.warning(f"[Графики] Новый файл {new_file_name} не найден")
                return []

            # Читаем полное расписание всех пользователей из старого файла
            logger.info("[График] Читаем старый файл...")
            old_schedules = extract_users_schedules(old_file_path)

            # Читаем полное расписание всех пользователей из нового файла
            logger.info("[График] Читаем новый файл...")
            new_schedules = extract_users_schedules(new_file_path)

            logger.info(
                f"[График] Найдено пользователей: старый файл - {len(old_schedules)}, новый файл - {len(new_schedules)}"
            )

            # Сравниваем расписания и находим изменения
            changes = []
            all_users = set(old_schedules.keys()) | set(new_schedules.keys())

            for fullname in all_users:
                # Проверяем, что пользователь есть в БД
                user = await stp_repo.employee.get_users(fullname=fullname)
                if not user:
                    continue

                old_schedule = old_schedules.get(fullname, {})
                new_schedule = new_schedules.get(fullname, {})

                change_details = compare_schedules(fullname, old_schedule, new_schedule)

                if change_details:
                    changes.append(change_details)

            return changes

        except Exception as e:
            logger.error(f"Error detecting schedule changes: {e}")
            return []

    async def _send_change_notification(
        self, bot, user_id: int, user_changes: Dict
    ) -> bool:
        """Отправляем сотруднику уведомление об изменении его графика.

        Args:
            bot: Экземпляр бота
            user_id: Идентификатор сотрудника Telegram
            user_changes: Словарь с данными об измененных днях графика

        Returns:
            True если уведомление было отправлено успешно
        """
        try:
            fullname = user_changes["fullname"]
            changes = user_changes["changes"]

            from datetime import datetime

            current_time = datetime.now(tz)

            # Используем форматтер для генерации сообщения
            message = self.formatter.format_change_notification(
                fullname, changes, current_time
            )

            # Отправка уведомления
            success = await send_message(
                bot=bot,
                user_id=user_id,
                text=message,
                disable_notification=False,
                reply_markup=changed_schedule_kb(),
            )

            if success:
                logger.info(
                    f"[График] Уведомление об изменении графика отправлено {fullname} (ID: {user_id})"
                )
            else:
                logger.warning(
                    f"[График] Ошибка отправки уведомления об изменении графика {fullname} (ID: {user_id})"
                )

            return success

        except Exception as e:
            logger.error(f"[График] Ошибка отправки уведомления: {e}")
            return False

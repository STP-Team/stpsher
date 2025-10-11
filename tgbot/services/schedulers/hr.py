"""HR-планировщик для управления кадровыми процессами

Содержит задачи по обработке увольнений, уведомлениям об авторизации
и другим кадровым операциям.
"""

import logging
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from stp_database import MainRequestsRepo
from stp_database.repo.STP.employee import EmployeeRepo

from tgbot.services.broadcaster import send_message
from tgbot.services.schedulers.base import BaseScheduler

logger = logging.getLogger(__name__)


class HRScheduler(BaseScheduler):
    """Планировщик HR-задач

    Управляет задачами связанными с кадровыми процессами:
    - Обработка увольнений из Excel файлов
    - Уведомления об неавторизованных пользователях
    """

    def __init__(self):
        super().__init__("HR")

    def setup_jobs(self, scheduler: AsyncIOScheduler, session_pool, bot: Bot):
        """Настройка всех HR задач"""
        self.logger.info("Настройка HR задач...")

        # Задача обработки увольнений - каждый день в 9:00
        scheduler.add_job(
            func=self._process_fired_users_job,
            args=[session_pool, bot],
            trigger="cron",
            id="hr_process_fired_users",
            name="Обработка увольнений",
            hour=9,
            minute=0,
        )

        # Запуск обработки увольнений при старте
        scheduler.add_job(
            func=self._process_fired_users_job,
            args=[session_pool, bot],
            trigger="date",
            id="hr_startup_process_fired_users",
            name="Запуск при старте: Обработка увольнений",
            run_date=None,
        )

        # Задача уведомлений о неавторизованных пользователях - каждый день в 10:30
        self._add_job(
            scheduler=scheduler,
            func=self._notify_unauthorized_users_job,
            args=[session_pool, bot],
            trigger="cron",
            job_id="notify_unauthorized_users",
            name="Уведомления о неавторизованных пользователях",
            hour=10,
            minute=30,
        )

    async def _process_fired_users_job(self, session_pool, bot: Bot):
        """Обёртка для задачи обработки увольнений"""
        self._log_job_execution_start("Обработка увольнений")
        try:
            await process_fired_users(session_pool, bot)
            self._log_job_execution_end("Обработка увольнений", success=True)
        except Exception as e:
            self._log_job_execution_end(
                "Обработка увольнений", success=False, error=str(e)
            )

    async def _notify_unauthorized_users_job(self, session_pool, bot: Bot):
        """Обёртка для задачи уведомлений об авторизации"""
        self._log_job_execution_start("Уведомления о неавторизованных пользователях")
        try:
            await notify_to_unauthorized_users(session_pool, bot)
            self._log_job_execution_end(
                "Уведомления о неавторизованных пользователях", success=True
            )
        except Exception as e:
            self._log_job_execution_end(
                "Уведомления о неавторизованных пользователях",
                success=False,
                error=str(e),
            )


# Функции для работы с увольнениями
def parse_dismissal_date(date_str: str) -> datetime:
    """Парсинг даты увольнения из формата '04.авг' или '25.июл'

    Args:
        date_str: Строка даты в формате 'день.месяц_сокр'

    Returns:
        datetime объект с текущим годом
    """
    month_mapping = {
        "янв": 1,
        "фев": 2,
        "мар": 3,
        "апр": 4,
        "май": 5,
        "июн": 6,
        "июл": 7,
        "авг": 8,
        "сен": 9,
        "окт": 10,
        "ноя": 11,
        "дек": 12,
    }

    parts = date_str.strip().split(".")
    if len(parts) != 2:
        raise ValueError(f"Неверный формат даты: {date_str}")

    day_str, month_str = parts
    day = int(day_str)

    month_str = month_str.lower()
    if month_str not in month_mapping:
        raise ValueError(f"Неизвестный месяц: {month_str}")

    month = month_mapping[month_str]
    current_year = datetime.now().year

    return datetime(current_year, month, day)


def get_fired_users_from_excel(files_list: list[str] = None) -> List[str]:
    """Получение списка уволенных сотрудников из Excel файлов

    Returns:
        Список ФИО уволенных сотрудников, дата увольнения которых совпадает с текущей датой
    """
    fired_users = []
    uploads_path = Path("uploads")
    current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if not uploads_path.exists():
        logger.warning("[Увольнения] Папка uploads не найдена")
        return fired_users

    if not files_list:
        schedule_files = []
        for root, dirs, files in os.walk(uploads_path, followlinks=True):
            for name in files:
                if name.startswith("ГРАФИК") and name.endswith(".xlsx"):
                    schedule_files.append(Path(root) / name)

        if not schedule_files:
            logger.info("[Увольнения] Файлы графиков не найдены")
            return fired_users
    else:
        schedule_files = []
        for file_name in files_list:
            for root, dirs, files in os.walk(uploads_path, followlinks=True):
                for name in files:
                    if Path(name).match(file_name):
                        schedule_files.append(Path(root) / name)

    for file_path in schedule_files:
        try:
            logger.info(f"[Увольнения] Обрабатываем файл: {file_path.name}")

            try:
                df = pd.read_excel(file_path, sheet_name="ЗАЯВЛЕНИЯ", header=None)
            except Exception as e:
                logger.debug(
                    f"[Увольнения] Лист ЗАЯВЛЕНИЯ не найден в {file_path.name}: {e}"
                )
                continue

            for row_idx in range(len(df)):
                try:
                    fullname = (
                        str(df.iloc[row_idx, 0])
                        if pd.notna(df.iloc[row_idx, 0])
                        else ""
                    )
                    dismissal_date = (
                        df.iloc[row_idx, 1] if pd.notna(df.iloc[row_idx, 1]) else None
                    )
                    dismissal_type = (
                        str(df.iloc[row_idx, 2])
                        if pd.notna(df.iloc[row_idx, 2])
                        else ""
                    )

                    if dismissal_type.strip().lower() not in ["увольнение", "декрет"]:
                        continue
                    if not fullname:
                        continue
                    if dismissal_date is None:
                        continue

                    if dismissal_date < current_date:
                        fired_users.append(fullname.strip())
                        logger.debug(
                            f"[Увольнения] Найден увольняемый сотрудник: {fullname.strip()}"
                        )

                except Exception as e:
                    logger.debug(
                        f"[Увольнения] Ошибка обработки строки {row_idx} в файле {file_path.name}: {e}"
                    )
                    continue

        except Exception as e:
            logger.error(f"[Увольнения] Ошибка обработки файла {file_path}: {e}")
            continue

    logger.info(f"[Увольнения] Найдено {len(fired_users)} сотрудников для увольнения")
    return fired_users


async def process_fired_users(session_pool, bot: Bot = None):
    """Обработка уволенных сотрудников - удаление из базы и групп

    Args:
        session_pool: Пул сессий БД из bot.py
        bot: Экземпляр бота для операций в Telegram (опционально)
    """
    try:
        fired_users = get_fired_users_from_excel()

        if not fired_users:
            logger.info("[Увольнения] Нет сотрудников для увольнения на сегодня")
            return

        # Получение сессии из пула
        async with session_pool() as session:
            user_repo = EmployeeRepo(session)

            total_deleted = 0
            for fullname in fired_users:
                try:
                    deleted_count = await user_repo.delete_user(fullname)
                    total_deleted += deleted_count
                    if deleted_count > 0:
                        logger.info(
                            f"[Увольнения] Сотрудник {fullname} - удалено {deleted_count} записей из БД"
                        )
                    else:
                        logger.debug(
                            f"[Увольнения] Сотрудник {fullname} не найден в БД"
                        )
                except Exception as e:
                    logger.error(
                        f"[Увольнения] Ошибка удаления сотрудника {fullname}: {e}"
                    )

            logger.info(
                f"[Увольнения] Обработка завершена. Удалено {total_deleted} записей для {len(fired_users)} сотрудников"
            )

        # Если передан экземпляр бота, удаляем сотрудников из групп
        if bot and fired_users:
            await remove_fired_users_from_groups(session_pool, bot, fired_users)

    except Exception as e:
        logger.error(f"[Увольнения] Критическая ошибка при обработке увольнений: {e}")


async def remove_fired_users_from_groups(
    session_pool, bot: Bot, fired_users: List[str]
):
    """Удаление уволенных сотрудников из групп с опцией remove_unemployed = True

    Args:
        session_pool: Пул сессий БД
        bot: Экземпляр бота для выполнения операций в Telegram
        fired_users: Список ФИО уволенных сотрудников
    """
    try:
        if not fired_users:
            logger.info("[Увольнения] Нет сотрудников для удаления из групп")
            return

        async with session_pool() as session:
            stp_repo = MainRequestsRepo(session)

            total_removed_from_groups = 0
            total_banned_from_telegram = 0

            for fullname in fired_users:
                try:
                    # Получаем информацию о сотруднике
                    employee = await stp_repo.employee.get_users(fullname=fullname)

                    if not employee or not employee.user_id:
                        logger.debug(
                            f"[Увольнения] Сотрудник {fullname} не найден в БД или не имеет user_id"
                        )
                        continue

                    # Получаем все группы сотрудника
                    user_groups = await stp_repo.group_member.get_member_groups(
                        employee.user_id
                    )

                    if not user_groups:
                        logger.debug(
                            f"[Увольнения] Сотрудник {fullname} не состоит в группах"
                        )
                        continue

                    # Проверяем каждую группу на наличие опции remove_unemployed
                    groups_removed_from = 0
                    groups_banned_from = 0

                    for group_membership in user_groups:
                        group = await stp_repo.group.get_group(
                            group_membership.group_id
                        )

                        if not group:
                            logger.debug(
                                f"[Увольнения] Группа {group_membership.group_id} не найдена в БД"
                            )
                            continue

                        if not group.remove_unemployed:
                            logger.debug(
                                f"[Увольнения] Группа {group_membership.group_id} не настроена на удаление уволенных"
                            )
                            continue

                        # Удаляем из БД
                        db_removed = await stp_repo.group_member.remove_member(
                            group_membership.group_id, employee.user_id
                        )

                        if db_removed:
                            groups_removed_from += 1
                            logger.info(
                                f"[Увольнения] Сотрудник {fullname} удален из БД группы {group_membership.group_id}"
                            )

                            # Пытаемся заблокировать в Telegram
                            try:
                                await bot.ban_chat_member(
                                    chat_id=group_membership.group_id,
                                    user_id=employee.user_id,
                                )
                                groups_banned_from += 1
                                logger.info(
                                    f"[Увольнения] Сотрудник {fullname} заблокирован в группе {group_membership.group_id}"
                                )
                            except Exception as telegram_error:
                                logger.warning(
                                    f"[Увольнения] Не удалось заблокировать {fullname} в группе {group_membership.group_id}: {telegram_error}"
                                )
                        else:
                            logger.warning(
                                f"[Увольнения] Не удалось удалить {fullname} из БД группы {group_membership.group_id}"
                            )

                    total_removed_from_groups += groups_removed_from
                    total_banned_from_telegram += groups_banned_from

                    if groups_removed_from > 0:
                        logger.info(
                            f"[Увольнения] Сотрудник {fullname}: удален из {groups_removed_from} групп в БД, "
                            f"заблокирован в {groups_banned_from} групп"
                        )

                except Exception as e:
                    logger.error(
                        f"[Увольнения] Ошибка обработки групп для сотрудника {fullname}: {e}"
                    )

            logger.info(
                f"[Увольнения] Обработка групп завершена: удалено из БД {total_removed_from_groups} записей, "
                f"заблокировано в Telegram {total_banned_from_telegram} записей"
            )

    except Exception as e:
        logger.error(f"[Увольнения] Критическая ошибка при удалении из групп: {e}")


# Функции для работы с авторизацией
async def notify_to_unauthorized_users(session_pool, bot: Bot):
    """Уведомление руководителей о неавторизованных пользователях в их группах"""
    try:
        async with session_pool() as session:
            stp_repo = MainRequestsRepo(session)
            unauthorized_users = await stp_repo.employee.get_unauthorized_users()

            if not unauthorized_users:
                logger.info("[Авторизация] Неавторизованных пользователей не найдено")
                return None

            logger.info(
                f"[Авторизация] Найдено {len(unauthorized_users)} неавторизованных пользователей"
            )

            # Группируем неавторизованных пользователей по руководителям
            unauthorized_by_head = await group_users_by_supervisor(unauthorized_users)

            # Отправляем уведомления руководителям
            notification_results = await send_notifications_to_supervisors(
                unauthorized_by_head, bot, stp_repo
            )

            # Логируем результаты
            total_notifications = sum(notification_results.values())
            logger.info(
                f"[Авторизация] Отправлено уведомлений: {total_notifications} из {len(notification_results)} руководителям"
            )

            return notification_results

    except Exception as e:
        logger.error(
            f"[Авторизация] Критическая ошибка при уведомлении об авторизации: {e}"
        )
        return {}


async def group_users_by_supervisor(unauthorized_users: List) -> Dict[str, List]:
    """Группирует неавторизованных пользователей по их руководителям

    Args:
        unauthorized_users: Список неавторизованных пользователей

    Returns:
        Словарь {имя_руководителя: [список_неавторизованных_подчиненных]}
    """
    unauthorized_by_head = defaultdict(list)
    users_without_head = []

    for user in unauthorized_users:
        if user.head and user.head.strip():
            # Фильтруем служебные email-адреса
            if "@ertelecom.ru" not in user.head:
                unauthorized_by_head[user.head].append(user)
            else:
                users_without_head.append(user)
        else:
            users_without_head.append(user)

    if users_without_head:
        logger.warning(
            f"[Авторизация] {len(users_without_head)} пользователей без руководителя: "
            f"{[user.fullname for user in users_without_head]}"
        )

    logger.info(
        f"[Авторизация] Группировка по руководителям: {len(unauthorized_by_head)} групп"
    )
    return dict(unauthorized_by_head)


async def send_notifications_to_supervisors(
    unauthorized_by_head: Dict[str, List], bot: Bot, stp_repo: MainRequestsRepo
) -> Dict[str, bool]:
    """Отправляет уведомления руководителям об их неавторизованных подчиненных

    Args:
        unauthorized_by_head: Словарь с группировкой пользователей по руководителям
        bot: Экземпляр бота для отправки сообщений
        stp_repo: Репозиторий для работы с БД

    Returns:
        Словарь с результатами отправки уведомлений {имя_руководителя: успех}
    """
    notification_results = {}

    for head_name, subordinates in unauthorized_by_head.items():
        try:
            # Ищем руководителя в БД
            supervisor = await stp_repo.employee.get_users(fullname=head_name)

            if not supervisor or not supervisor.user_id:
                logger.warning(
                    f"[Авторизация] Руководитель {head_name} не найден в БД или не имеет user_id"
                )
                notification_results[head_name] = False
                continue

            # Формируем сообщение
            message = create_notification_message(head_name, subordinates)

            # Отправляем уведомление
            success = await send_message(bot, supervisor.user_id, message)
            notification_results[head_name] = success

            if success:
                logger.info(
                    f"[Авторизация] Отправлено уведомление руководителю {head_name} "
                    f"о {len(subordinates)} неавторизованных подчиненных"
                )
            else:
                logger.error(
                    f"[Авторизация] Не удалось отправить уведомление руководителю {head_name}"
                )

        except Exception as e:
            logger.error(f"[Авторизация] Ошибка отправки уведомления {head_name}: {e}")
            notification_results[head_name] = False

    return notification_results


def create_notification_message(head_name: str, unauthorized_subordinates: List) -> str:
    """Создает текст уведомления для руководителя

    Args:
        head_name: Имя руководителя
        unauthorized_subordinates: Список неавторизованных подчиненных

    Returns:
        Готовый текст сообщения
    """
    subordinates_count = len(unauthorized_subordinates)

    # Формируем заголовок
    message_parts = [
        "🔔 <b>Неавторизованные сотрудники</b>\n",
        f"Привет, <b>{head_name}</b>!\n",
        f"В твоей группе обнаружено <b>{subordinates_count}</b> неавторизованных сотрудника(ов):\n",
    ]

    # Добавляем список неавторизованных сотрудников
    for i, subordinate in enumerate(unauthorized_subordinates, 1):
        # Формируем строку с информацией о сотруднике
        user_info = f"{i}. <b>{subordinate.fullname}</b>"

        if subordinate.position and subordinate.division:
            user_info += f"\n💼 {subordinate.position} {subordinate.division}"

        message_parts.append(user_info)

    # Добавляем призыв к действию
    message_parts.extend([
        "\n💡 <b>Что нужно сделать:</b>",
        "• Попроси сотрудников авторизоваться в @stpsher_bot",
        "\n📋 <b>Для авторизации сотруднику необходимо:</b>",
        "1️⃣ Перейти в @stpsher_bot",
        "2️⃣ Нажать /start",
        "3️⃣ Следовать инструкциям бота",
        "\n❗ <b>Важно:</b> Авторизация необходима для корректной работы бота",
    ])

    return "\n".join(message_parts)


def format_unauthorized_users_summary(unauthorized_users: List) -> str:
    """Форматирует краткую сводку о неавторизованных пользователях для логов

    Args:
        unauthorized_users: Список неавторизованных пользователей

    Returns:
        Строка с краткой информацией
    """
    if not unauthorized_users:
        return "Неавторизованных пользователей не найдено"

    # Группируем по подразделениям
    divisions = defaultdict(int)
    for user in unauthorized_users:
        division = user.division if user.division else "Не указано"
        divisions[division] += 1

    # Формируем сводку
    summary_parts = [f"Всего неавторизованных: {len(unauthorized_users)}"]
    for division, count in divisions.items():
        summary_parts.append(f"• {division}: {count}")

    return ", ".join(summary_parts)

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd
import pytz
from apscheduler.jobstores.base import BaseJobStore
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from infrastructure.database.repo.users import UserRepo
from tgbot.config import load_config

config = load_config(".env")

scheduler = AsyncIOScheduler()

job_defaults = {
    "coalesce": True,
    "misfire_grace_time": 300,
    "replace_existing": True,
}

jobstores: Dict[str, BaseJobStore] = {"default": MemoryJobStore()}

if config.tg_bot.use_redis:
    REDIS = {
        "host": config.redis.redis_host,
        "port": config.redis.redis_port,
        "password": config.redis.redis_pass,
        "db": 1,
        "ssl": False,
        "decode_responses": False,
    }
    jobstores["redis"] = RedisJobStore(**REDIS)

scheduler.configure(
    jobstores=jobstores,
    job_defaults=job_defaults,
    timezone=pytz.timezone("Asia/Yekaterinburg"),
)

logger = logging.getLogger(__name__)


def parse_dismissal_date(date_str: str) -> datetime:
    """
    Парсинг даты увольнения из формата '04.авг' или '25.июл'

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


def get_fired_users_from_excel() -> List[str]:
    """
    Получение списка уволенных сотрудников из Excel файлов

    Returns:
        Список ФИО уволенных сотрудников, дата увольнения которых совпадает с текущей датой
    """
    fired_users = []
    uploads_path = Path("uploads")
    current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if not uploads_path.exists():
        logger.warning("[Увольнения] Папка uploads не найдена")
        return fired_users

    # Поиск файлов с названием "ГРАФИК*"
    schedule_files = list(uploads_path.glob("ГРАФИК*.xlsx"))

    if not schedule_files:
        logger.info("[Увольнения] Файлы графиков не найдены")
        return fired_users

    for file_path in schedule_files:
        try:
            logger.info(f"[Увольнения] Обрабатываем файл: {file_path.name}")

            # Чтение листа "ЗАЯВЛЕНИЯ"
            try:
                df = pd.read_excel(file_path, sheet_name="ЗАЯВЛЕНИЯ", header=None)
            except Exception as e:
                logger.debug(
                    f"[Увольнения] Лист ЗАЯВЛЕНИЯ не найден в {file_path.name}: {e}"
                )
                continue

            # Поиск строк с увольнениями
            for row_idx in range(len(df)):
                try:
                    # Колонка A - ФИО, B - дата, C - тип заявления
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

                    # Проверяем, что это увольнение
                    if dismissal_type.strip().lower() != "увольнение":
                        continue

                    # Проверяем ФИО (не пустое и содержит буквы)
                    if not fullname:
                        continue

                    # Проверяем дату увольнения
                    if dismissal_date is None:
                        continue

                    # Проверяем, если дата увольнения старше или равна сегодняшней дате
                    if dismissal_date <= current_date:
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


async def process_fired_users(session_pool):
    """
    Обработка уволенных сотрудников - удаление из базы данных

    Args:
        session_pool: Пул сессий БД из bot.py
    """
    try:
        fired_users = get_fired_users_from_excel()

        if not fired_users:
            logger.info("[Увольнения] Нет сотрудников для увольнения на сегодня")
            return

        # Получение сессии из пула
        async with session_pool() as session:
            user_repo = UserRepo(session)

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

    except Exception as e:
        logger.error(f"[Увольнения] Критическая ошибка при обработке увольнений: {e}")

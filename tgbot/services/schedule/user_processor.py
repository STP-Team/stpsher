"""
User processing service for handling Excel-based user data changes.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from infrastructure.database.models import User
from infrastructure.database.repo.user import UserRepo
from tgbot.services.scheduler import get_fired_users_from_excel

logger = logging.getLogger(__name__)


async def process_user_changes(session_pool, file_name: str):
    """
    Процессинг изменений должности и руководителя специалиста из файла.

    Args:
        session_pool: Сессия с БД
        file_name: Название файла с таблицей
    """
    try:
        logger.info(f"[Изменения] Проверка изменений в файле: {file_name}")

        division = extract_division_from_filename(file_name)
        excel_users = get_users_from_excel(file_name)

        if not excel_users:
            logger.info("[Изменения] Пользователи не найдены в файле")
            return

        fired_users = get_fired_users_from_excel()

        async with session_pool() as session:
            user_repo = UserRepo(session)
            total_updated, total_added = 0, 0

            for excel_user in excel_users:
                fullname = excel_user["fullname"]

                if fullname == "Стажеры общего ряда":
                    break

                if fullname in fired_users:
                    logger.debug(f"[Изменения] Пропускаем уволенного: {fullname}")
                    continue

                try:
                    db_user = await user_repo.get_user(fullname=fullname)

                    if db_user:
                        total_updated += await _update_existing_user(
                            db_user, excel_user
                        )
                    else:
                        await _add_new_user(session, division, excel_user)
                        total_added += 1

                except Exception as e:
                    logger.error(
                        f"[Изменения] Ошибка обработки пользователя {fullname}: {e}"
                    )

            if total_updated > 0 or total_added > 0:
                await session.commit()
                logger.info(
                    f"[Изменения] Обновлено {total_updated}, добавлено {total_added} пользователей"
                )
            else:
                logger.info("[Изменения] Нет изменений для применения")

    except Exception as e:
        logger.error(f"[Изменения] Критическая ошибка при обработке изменений: {e}")


async def _update_existing_user(db_user: User, excel_user: Dict[str, str]) -> int:
    """Update existing user with new data. Returns 1 if updated, 0 if no changes."""
    updated = False

    if db_user.position != excel_user["position"]:
        logger.info(
            f"[Изменения] {db_user.fullname}: должность {db_user.position} → {excel_user['position']}"
        )
        db_user.position = excel_user["position"]
        updated = True

    if db_user.head != excel_user["head"]:
        logger.info(
            f"[Изменения] {db_user.fullname}: руководитель {db_user.head} → {excel_user['head']}"
        )
        db_user.head = excel_user["head"]
        updated = True

    return 1 if updated else 0


async def _add_new_user(session, division: str, excel_user: Dict[str, str]):
    """Add new user to database."""
    new_user = User(
        division=division,
        position=excel_user["position"],
        fullname=excel_user["fullname"],
        head=excel_user["head"],
        role=0,
    )
    session.add(new_user)
    logger.info(f"[Изменения] Добавлен новый пользователь: {excel_user['fullname']}")


def extract_division_from_filename(filename: str) -> str:
    """Extract division from filename."""
    filename_upper = filename.upper()

    division_map = {"НЦК": "НЦК", "НТП1": "НТП1", "НТП2": "НТП2", "НТП": "НТП"}

    for key, value in division_map.items():
        if key in filename_upper:
            return value

    return "НТП"  # Default


def get_users_from_excel(file_name: str) -> List[Dict[str, str]]:
    """
    Extract users from Excel file with structure:
    ДАТА → График Город ПРМ Должность Руководитель 1 смена...

    Args:
        file_name: Excel file name

    Returns:
        List of user dictionaries with fullname, position, head
    """
    users = []
    file_path = Path("uploads") / file_name

    if not file_path.exists():
        logger.warning(f"[Изменения] Файл {file_name} не найден")
        return users

    try:
        logger.info(f"[Изменения] Читаем пользователей из файла: {file_name}")
        df = pd.read_excel(file_path, sheet_name=0, header=None)

        header_info = _find_header_columns(df)
        if not header_info:
            logger.warning(
                f"[Изменения] Не найдены необходимые колонки в файле {file_name}"
            )
            return users

        users = _extract_users_from_dataframe(df, header_info)
        logger.info(f"[Изменения] Найдено {len(users)} пользователей в файле")
        return users

    except Exception as e:
        logger.error(f"[Изменения] Ошибка чтения файла {file_name}: {e}")
        return users


def _find_header_columns(df: pd.DataFrame) -> Optional[Dict[str, int]]:
    """Find header row and column positions."""
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
            logger.info(
                f"[Изменения] Найдена строка заголовков: {row_idx}, колонки - ФИО: 0, Должность: {position_col}, Руководитель: {head_col}"
            )
            return {
                "header_row": row_idx,
                "fullname_col": 0,
                "position_col": position_col,
                "head_col": head_col,
            }

    return None


def _extract_users_from_dataframe(
    df: pd.DataFrame, header_info: Dict[str, int]
) -> List[Dict[str, str]]:
    """Extract user data from dataframe."""
    users = []

    for row_idx in range(header_info["header_row"] + 1, len(df)):
        fullname_cell = (
            str(df.iloc[row_idx, header_info["fullname_col"]])
            if pd.notna(df.iloc[row_idx, header_info["fullname_col"]])
            else ""
        )
        position_cell = (
            str(df.iloc[row_idx, header_info["position_col"]])
            if pd.notna(df.iloc[row_idx, header_info["position_col"]])
            else ""
        )
        head_cell = (
            str(df.iloc[row_idx, header_info["head_col"]])
            if pd.notna(df.iloc[row_idx, header_info["head_col"]])
            else ""
        )

        if _is_valid_fullname(fullname_cell):
            fullname = fullname_cell.strip()
            position = (
                position_cell.strip()
                if position_cell.strip() not in ["", "nan", "None"]
                else "Специалист"
            )
            head = (
                head_cell.strip()
                if head_cell.strip() not in ["", "nan", "None"]
                else ""
            )

            users.append({"fullname": fullname, "position": position, "head": head})

    return users


def _is_valid_fullname(fullname_cell: str) -> bool:
    """Check if cell contains valid fullname."""
    return (
        len(fullname_cell.split()) >= 3
        and re.search(r"[А-Яа-я]", fullname_cell)
        and not re.search(r"\d", fullname_cell)
        and fullname_cell.strip() not in ["", "nan", "None"]
    )


async def process_fired_users_with_stats(session_pool):
    """
    Обработка уволенных сотрудников - удаление из базы данных
    Returns list of fired user names for statistics

    Args:
        session_pool: Пул сессий БД из bot.py

    Returns:
        list: Names of fired users processed
    """
    try:
        fired_users = get_fired_users_from_excel()

        if not fired_users:
            logger.info("[Увольнения] Нет сотрудников для увольнения на сегодня")
            return []

        # Получение сессии из пула
        async with session_pool() as session:
            user_repo = UserRepo(session)

            fired_names = []
            total_deleted = 0

            for fullname in fired_users:
                try:
                    deleted_count = await user_repo.delete_user(fullname)
                    total_deleted += deleted_count
                    if deleted_count > 0:
                        fired_names.append(fullname)
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

            return fired_names

    except Exception as e:
        logger.error(f"[Увольнения] Критическая ошибка при обработке увольнений: {e}")
        return []


async def process_user_changes_with_stats(session_pool, file_name: str):
    """
    Процессинг изменений должности и руководителя специалиста из файла.
    Returns lists of updated and new user names

    Args:
        session_pool: Сессия с БД
        file_name: Название файла с таблицей

    Returns:
        tuple: (updated_names, new_names)
    """
    try:
        logger.info(f"[Изменения] Проверка изменений в файле: {file_name}")

        division = extract_division_from_filename(file_name)
        excel_users = get_users_from_excel(file_name)

        if not excel_users:
            logger.info("[Изменения] Пользователи не найдены в файле")
            return [], []

        fired_users = get_fired_users_from_excel()

        async with session_pool() as session:
            user_repo = UserRepo(session)
            updated_names = []
            new_names = []

            for excel_user in excel_users:
                fullname = excel_user["fullname"]

                if fullname == "Стажеры общего ряда":
                    break

                if fullname in fired_users:
                    logger.debug(f"[Изменения] Пропускаем уволенного: {fullname}")
                    continue

                try:
                    db_user = await user_repo.get_user(fullname=fullname)

                    if db_user:
                        was_updated = await _update_existing_user(db_user, excel_user)
                        if was_updated:
                            updated_names.append(fullname)
                    else:
                        await _add_new_user(session, division, excel_user)
                        new_names.append(fullname)

                except Exception as e:
                    logger.error(
                        f"[Изменения] Ошибка обработки пользователя {fullname}: {e}"
                    )

            if updated_names or new_names:
                await session.commit()
                logger.info(
                    f"[Изменения] Обновлено {len(updated_names)}, добавлено {len(new_names)} пользователей"
                )
            else:
                logger.info("[Изменения] Нет изменений для применения")

            return updated_names, new_names

    except Exception as e:
        logger.error(f"[Изменения] Критическая ошибка при обработке изменений: {e}")
        return [], []

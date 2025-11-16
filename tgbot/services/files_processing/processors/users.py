"""User processing service for handling Excel-based user data changes."""

import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from stp_database import Employee
from stp_database.repo.STP.employee import EmployeeRepo

from tgbot.services.schedulers.hr import get_fired_users_from_excel

from ..parsers.base import BaseParser
from ..utils.files import find_header_columns
from ..utils.schedule import extract_division_from_filename

logger = logging.getLogger(__name__)


async def _update_existing_user(db_user: Employee, excel_user: Dict[str, str]) -> bool:
    """Обновляет сотрудника в БД с новыми данными. Returns 1 if updated, 0 if no changes.

    Args:
        db_user: Сотрудник из БД
        excel_user: Сотрудник из Excel файла

    Returns:
        True если сотрудник был обновлен, иначе False
    """
    updated = False
    is_in_transfer_section = excel_user.get("is_in_transfer_section", False)

    # Обновляем должность только если пользователь не в секции переводов
    if not is_in_transfer_section and db_user.position != excel_user["position"]:
        logger.info(
            f"[Изменения] {db_user.fullname}: должность {db_user.position} → {excel_user['position']}"
        )
        db_user.position = excel_user["position"]
        updated = True
    elif is_in_transfer_section and db_user.position != excel_user["position"]:
        logger.info(
            f"[Изменения] {db_user.fullname}: игнорируем изменение должности (пользователь в секции переводов)"
        )

    if db_user.head != excel_user["head"]:
        logger.info(
            f"[Изменения] {db_user.fullname}: руководитель {db_user.head} → {excel_user['head']}"
        )
        db_user.head = excel_user["head"]
        updated = True

    return True if updated else False


def get_users_from_excel(file_name: str) -> List[Dict[str, str]]:
    """Достает сотрудников из файла графиков Excel.

    Формат: ДАТА → График Город ПРМ Должность Руководитель 1 смена.

    Args:
        file_name: Название файла Excel

    Returns:
        Список словарей сотрудник с ФИО, должностью и руководителем
    """
    users = []
    file_path = Path("uploads") / file_name

    if not file_path.exists():
        logger.warning(f"[Изменения] Файл {file_name} не найден")
        return users

    try:
        logger.info(f"[Изменения] Читаем пользователей из файла: {file_name}")
        df = pd.read_excel(file_path, sheet_name=0, header=None)

        header_info = find_header_columns(df)
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


def _extract_users_from_dataframe(
    df: pd.DataFrame, header_info: Dict[str, int]
) -> List[Dict[str, str]]:
    """Достает пользователей из датафрейма.

    Args:
        df: Датафрейм
        header_info: Заголовок колонки

    Returns:
        Список словарей сотрудников из датафрейма
    """
    users = []
    transfer_section_row = None

    # Находим строку "Переводы/увольнения"
    for row_idx in range(header_info["header_row"] + 1, len(df)):
        fullname_cell = (
            str(df.iloc[row_idx, header_info["fullname_col"]])
            if pd.notna(df.iloc[row_idx, header_info["fullname_col"]])
            else ""
        )
        if (
            "переводы" in fullname_cell.lower()
            and "увольнения" in fullname_cell.lower()
        ):
            transfer_section_row = row_idx
            logger.info(
                f"[Изменения] Найдена секция 'Переводы/увольнения' в строке {row_idx}"
            )
            break

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

        if BaseParser.is_valid_fullname(fullname_cell):
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

            # Mark if user is in transfer section
            is_in_transfer_section = (
                transfer_section_row is not None and row_idx > transfer_section_row
            )

            users.append({
                "fullname": fullname,
                "position": position,
                "head": head,
                "is_in_transfer_section": is_in_transfer_section,
            })

    return users


async def process_fired_users_with_stats(
    files_list: list[str] | list[Path],
    stp_session_pool: async_sessionmaker[AsyncSession],
) -> list[Any]:
    """Обработка уволенных сотрудников - удаление из базы.

    Args:
        files_list: Список файлов для проверки
        stp_session_pool: Пул сессий с базой STP

    Returns:
         Список фио уволенных специалистов
    """
    try:
        fired_users = get_fired_users_from_excel(files_list)

        if not fired_users:
            logger.info("[Увольнения] Нет сотрудников для увольнения на сегодня")
            return []

        # Получение сессии из пула
        async with stp_session_pool() as session:
            user_repo = EmployeeRepo(session)

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


async def process_user_changes(
    stp_session_pool: async_sessionmaker[AsyncSession], file_name: str
):
    """Процессинг изменений должности и руководителя специалиста из файла.

    Args:
        stp_session_pool: Пул сессий с базой STP
        file_name: Название файла с таблицей

    Returns:
        Список имен обновленных и новых сотрудников
    """
    try:
        logger.info(f"[Изменения] Проверка изменений в файле: {file_name}")

        division = extract_division_from_filename(file_name)
        excel_users = get_users_from_excel(file_name)

        if not excel_users:
            logger.info("[Изменения] Пользователи не найдены в файле")
            return [], []

        fired_users = get_fired_users_from_excel([file_name])

        async with stp_session_pool() as session:
            user_repo = EmployeeRepo(session)
            db_users = await user_repo.get_users()
            existing_fullnames = [user.fullname for user in db_users]
            updated_names = []
            new_names = []

            for excel_user in excel_users:
                fullname = excel_user["fullname"]

                if fullname == "Стажеры общего ряда":
                    continue

                if fullname in existing_fullnames and fullname in fired_users:
                    await user_repo.delete_user(fullname=fullname)
                    logger.info(f"[Изменения] Удален уволенный: {fullname}")

                if fullname in fired_users:
                    logger.info(f"[Изменения] Пропущен уволенный: {fullname}")
                    continue

                try:
                    # Получает список существующих ФИО
                    if fullname in existing_fullnames:
                        # Находим конкретного сотрудника
                        db_user = next(
                            (user for user in db_users if user.fullname == fullname),
                            None,
                        )
                        if db_user:
                            was_updated = await _update_existing_user(
                                db_user, excel_user
                            )
                            if was_updated:
                                updated_names.append(fullname)
                    else:
                        is_in_transfer_section = excel_user.get(
                            "is_in_transfer_section", False
                        )
                        if not is_in_transfer_section:
                            new_user = await user_repo.add_user(
                                division=division,
                                position=excel_user["position"],
                                fullname=excel_user["fullname"],
                                head=excel_user["head"],
                                role=0,
                            )
                            if new_user:
                                new_names.append(fullname)
                        else:
                            logger.info(
                                f"[Изменения] Пропуск добавления {fullname} (в секции переводов)"
                            )

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

"""User processing service for handling Excel-based user data changes."""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.employee import EmployeeRepo
from tgbot.services.schedulers.hr import get_fired_users_from_excel

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


async def _add_new_user(session, division: str, excel_user: Dict[str, str]) -> None:
    """Добавляет пользователя в БД.

    Args:
        session: Сессия БД
        division: Направление сотрудника
        excel_user: Данные сотрудника из Excel файла
    """
    is_in_transfer_section = excel_user.get("is_in_transfer_section", False)
    if is_in_transfer_section:
        logger.info(
            f"[Изменения] Пропуск добавления нового пользователя {excel_user['fullname']} (в секции переводов)"
        )
        return

    new_user = Employee(
        division=division,
        position=excel_user["position"],
        fullname=excel_user["fullname"],
        head=excel_user["head"],
        role=0,
        is_casino_allowed=True,
    )
    session.add(new_user)
    logger.info(f"[Изменения] Добавлен новый пользователь: {excel_user['fullname']}")


def extract_division_from_filename(filename: str) -> str:
    """Достает направление из названия файла.

    Args:
        filename: Название файла

    Returns:
        Направление, которому принадлежит файл
    """
    filename_upper = filename.upper()

    division_map = {"НЦК": "НЦК", "НТП1": "НТП1", "НТП2": "НТП2", "НТП": "НТП"}

    for key, value in division_map.items():
        if key in filename_upper:
            return value

    return "НТП"


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
    """Находит позиции строк и столбцов заголовка.

    Args:
        df: Датафрейм

    Returns:
        Строка заголовков
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


def _is_valid_fullname(fullname_cell: str) -> bool:
    """Проверяет содержит ли ячейка ФИО.

    Args:
        fullname_cell: Строка ячейки ФИО

    Returns:
        True если строка является ФИО, иначе False
    """
    return (
        len(fullname_cell.split()) >= 3
        and re.search(r"[А-Яа-я]", fullname_cell)
        and not re.search(r"\d", fullname_cell)
        and fullname_cell.strip() not in ["", "nan", "None"]
    )


async def process_fired_users_with_stats(
    files_list: list[str] | list[Path], session_pool
):
    """Обработка уволенных сотрудников - удаление из базы.

    Args:
        files_list: Список файлов для проверки
        session_pool: Пул сессий БД из bot.py

    Returns:
         ФИО уволенных специалистов
    """
    try:
        fired_users = get_fired_users_from_excel(files_list)

        if not fired_users:
            logger.info("[Увольнения] Нет сотрудников для увольнения на сегодня")
            return []

        # Получение сессии из пула
        async with session_pool() as session:
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


async def process_user_changes(session_pool, file_name: str):
    """Процессинг изменений должности и руководителя специалиста из файла.

    Args:
        session_pool: Сессия с БД
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

        async with session_pool() as session:
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
                            await _add_new_user(session, division, excel_user)
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

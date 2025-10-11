import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import pytz
from stp_database import Employee, MainRequestsRepo

from tgbot.keyboards.schedule import changed_schedule_kb
from tgbot.services.broadcaster import send_message

logger = logging.getLogger(__name__)


class ScheduleChangeDetector:
    """Сервис обнаружения и уведомления об изменениях в графиках пользователей."""

    def __init__(self, uploads_folder: str = "uploads"):
        self.uploads_folder = Path(uploads_folder)

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
                user: Employee = await stp_repo.employee.get_user(
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
            old_schedules = self._extract_users_schedules(old_file_path)

            # Читаем полное расписание всех пользователей из нового файла
            logger.info("[График] Читаем новый файл...")
            new_schedules = self._extract_users_schedules(new_file_path)

            logger.info(
                f"[График] Найдено пользователей: старый файл - {len(old_schedules)}, новый файл - {len(new_schedules)}"
            )

            # Сравниваем расписания и находим изменения
            changes = []
            all_users = set(old_schedules.keys()) | set(new_schedules.keys())

            for fullname in all_users:
                # Проверяем, что пользователь есть в БД
                user = await stp_repo.employee.get_user(fullname=fullname)
                if not user:
                    continue

                old_schedule = old_schedules.get(fullname, {})
                new_schedule = new_schedules.get(fullname, {})

                change_details = self._compare_schedules(
                    fullname, old_schedule, new_schedule
                )

                if change_details:
                    changes.append(change_details)

            return changes

        except Exception as e:
            logger.error(f"Error detecting schedule changes: {e}")
            return []

    def _extract_users_schedules(self, file_path: Path) -> Dict[str, Dict[str, str]]:
        """Извлекает полные расписания всех сотрудников из Excel файла за один проход.

        Использует ту же логику, что и рабочие парсеры, но для всех месяцев сразу.

        Args:
            file_path: Путь до проверяемого файла графиков

        Returns:
            Словарь с полным расписанием сотрудников за все месяцы
        """
        schedules = {}

        try:
            # Читаем файл графиков
            df = pd.read_excel(file_path, sheet_name=0, header=None, dtype=str)
            logger.debug(
                f"[График] Прочитан Excel файл {file_path}, размер: {df.shape}"
            )

            # Находим все месяцы и их диапазоны колонок
            months_ranges = self._find_all_months_ranges(df)
            if not months_ranges:
                logger.warning(f"[График] Месяцы не найдены в файле {file_path}")
                return schedules

            logger.info(f"[График] Найдены месяцы: {list(months_ranges.keys())}")

            # Находим всех пользователей в файле
            users_rows = self._find_all_users_rows(df)
            if not users_rows:
                logger.warning(f"[График] Пользователи не найдены в файле {file_path}")
                return schedules

            logger.info(f"[График] Найдено пользователей: {len(users_rows)}")

            # Для каждого пользователя извлекаем полное расписание по всем месяцам
            for fullname, row_idx in users_rows.items():
                user_complete_schedule = {}

                # Проходим по всем месяцам
                for month, (start_col, end_col) in months_ranges.items():
                    # Находим заголовки дней для этого месяца
                    day_headers = self._find_day_headers_in_range(
                        df, start_col, end_col
                    )

                    logger.debug(
                        f"[График] {fullname} - {month}: найдено {len(day_headers)} дней"
                    )

                    # Извлекаем значения расписания для этого месяца
                    for col_idx in range(start_col, end_col + 1):
                        if col_idx in day_headers:
                            day_name = day_headers[col_idx]
                            schedule_key = f"{month}_{day_name}"

                            if col_idx < len(df.columns):
                                schedule_value = (
                                    str(df.iloc[row_idx, col_idx])
                                    if pd.notna(df.iloc[row_idx, col_idx])
                                    else ""
                                )
                                user_complete_schedule[schedule_key] = (
                                    schedule_value.strip()
                                )

                schedules[fullname] = user_complete_schedule

            logger.info(
                f"[График] Извлечено полных расписаний: {len(schedules)} пользователей"
            )
            return schedules

        except Exception as e:
            logger.error(f"[График] Ошибка извлечения расписаний из {file_path}: {e}")
            return {}

    @staticmethod
    def _find_all_months_ranges(df: pd.DataFrame) -> Dict[str, tuple]:
        """Находит диапазоны колонок для всех месяцев в файле.

        Args:
            df: Датафрейм

        Returns:
            Словарь доступных диапазонов месяцев
        """
        months_ranges = {}
        months_order = [
            "ЯНВАРЬ",
            "ФЕВРАЛЬ",
            "МАРТ",
            "АПРЕЛЬ",
            "МАЙ",
            "ИЮНЬ",
            "ИЮЛЬ",
            "АВГУСТ",
            "СЕНТЯБРЬ",
            "ОКТЯБРЬ",
            "НОЯБРЬ",
            "ДЕКАБРЬ",
        ]

        def find_month_column(
            target_month: str, target_first_col: int = 0
        ) -> Optional[int]:
            """Находит колонку с указанным месяцем."""
            for col_idx in range(target_first_col, len(df.columns)):
                # Проверяем заголовки колонок
                col_name = (
                    str(df.columns[col_idx]).upper() if df.columns[col_idx] else ""
                )
                if target_month in col_name:
                    return col_idx

                # Проверяем первые строки
                for row_idx in range(min(5, len(df))):
                    val = (
                        df.iat[row_idx, col_idx]
                        if pd.notna(df.iat[row_idx, col_idx])
                        else ""
                    )
                    if isinstance(val, str) and target_month in val.upper():
                        return col_idx
            return None

        # Находим все месяцы по порядку
        last_end_col = 0
        for month in months_order:
            start_col = find_month_column(month, last_end_col)
            if start_col is not None:
                # Находим конец этого месяца (начало следующего месяца - 1)
                end_col = len(df.columns) - 1  # По умолчанию до конца файла

                # Ищем следующий месяц
                for next_month in months_order[months_order.index(month) + 1 :]:
                    next_start = find_month_column(next_month, start_col + 1)
                    if next_start is not None:
                        end_col = next_start - 1
                        break

                months_ranges[month] = (start_col, end_col)
                last_end_col = end_col + 1

        return months_ranges

    def _find_all_users_rows(self, df: pd.DataFrame) -> Dict[str, int]:
        """Находит строки всех пользователей в файле.

        Args:
            df: Датафрейм

        Returns:
            Словарь со списком пользователей и индекса строк, на которых они находятся
        """
        users_rows = {}

        for row_idx in range(len(df)):
            for col_idx in range(min(4, len(df.columns))):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )

                if self._is_valid_fullname(cell_value.strip()):
                    fullname = cell_value.strip()
                    users_rows[fullname] = row_idx
                    break

        return users_rows

    @staticmethod
    def _find_day_headers_in_range(
        df: pd.DataFrame, start_col: int, end_col: int
    ) -> Dict[int, str]:
        """Находит заголовки дней в указанном диапазоне колонок.

        Args:
            df: Датафрейм
            start_col: Стартовая колонка
            end_col: Конечная колонка

        Returns:
            Словарь заголовков дней
        """
        day_headers = {}

        for row_idx in range(min(5, len(df))):
            for col_idx in range(start_col, end_col + 1):
                cell_value = (
                    str(df.iloc[row_idx, col_idx])
                    if pd.notna(df.iloc[row_idx, col_idx])
                    else ""
                )

                # Паттерн: число (1-31) + 1-2 кириллические буквы
                day_with_weekday_pattern = r"^(\d{1,2})([А-Яа-я]{1,2})$"
                match = re.search(day_with_weekday_pattern, cell_value.strip())

                if match:
                    day_num = match.group(1)
                    day_abbr = match.group(2)

                    if 1 <= int(day_num) <= 31:
                        day_headers[col_idx] = f"{day_num}({day_abbr})"
                        logger.debug(
                            f"[График] Найден день: колонка {col_idx} = '{day_num}({day_abbr})' из '{cell_value}'"
                        )
                        continue

        logger.debug(
            f"[График] Найдено {len(day_headers)} дней в диапазоне колонок {start_col}-{end_col}: {list(day_headers.values())}"
        )
        return day_headers

    @staticmethod
    def _is_valid_fullname(text: str) -> bool:
        """Проверяет, является ли текст корректным ФИО."""
        if not text or text.strip() in ["", "nan", "None", "ДАТА →"]:
            return False

        text = text.strip()
        words = text.split()

        # Должно быть минимум 2 слова (фамилия + имя)
        if len(words) < 2:
            return False

        # Должны быть кириллические символы
        if not re.search(r"[А-Яа-я]", text):
            return False

        # Не должно быть цифр
        if re.search(r"\d", text):
            return False

        # Пропускаем служебные записи
        if text.upper() in ["СТАЖЕРЫ ОБЩЕГО РЯДА", "ДАТА"]:
            return False

        return True

    def _compare_schedules(
        self, fullname: str, old_schedule: Dict[str, str], new_schedule: Dict[str, str]
    ) -> Optional[Dict]:
        """Сравнивает расписания пользователя и возвращает детали изменений.

        Args:
            fullname: Полные ФИО
            old_schedule: Словарь со старым графиком сотрудника
            new_schedule: Словарь с новым графиком сотрудника

        Returns:
            Словарь с данными о днях с измененными графиками
        """
        changes = []

        # Получаем все дни из обоих расписаний
        all_days = set(old_schedule.keys()) | set(new_schedule.keys())

        for day in all_days:
            old_value = self._normalize_value(old_schedule.get(day, ""))
            new_value = self._normalize_value(new_schedule.get(day, ""))

            if old_value != new_value:
                # Очищаем название дня для отображения
                display_day = day.replace("_", " ").replace("(", " (")

                changes.append({
                    "day": display_day,
                    "old_value": old_value or "выходной",
                    "new_value": new_value or "выходной",
                })

        if changes:
            logger.info(
                f"[График] Найдены изменения для {fullname}: {len(changes)} дней"
            )
            # ОТЛАДКА: Добавляем детализированный лог изменений
            for change in changes:
                logger.debug(
                    f"[График] Изменение для {fullname} - {change['day']}: "
                    f"'{change['old_value']}' -> '{change['new_value']}'"
                )
            return {"fullname": fullname, "changes": changes}

        return None

    @staticmethod
    def _normalize_value(value: str) -> str:
        """Нормализует значение расписания для сравнения."""
        if not value or value.strip().lower() in ["", "nan", "none", "не указано", "0"]:
            return ""

        return value.strip()

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

            yekaterinburg_tz = pytz.timezone("Asia/Yekaterinburg")
            current_time = datetime.now(yekaterinburg_tz)

            message = f"🔔 <b>Изменения в графике</b> • {current_time.strftime('%d.%m.%Y')}\n\n"

            # Сортируем изменения по дате (от старых к новым)
            def parse_date_from_day(day_str) -> tuple[int | Any, int] | tuple[int, int]:
                """Достаем дату из строки дня.

                Args:
                    day_str: Строка с днем

                Returns:
                    Индекс месяца и дня
                """
                # Достаем индекс месяца и день из строк типа "АВГУСТ 24 (Вс)"
                month_map = {
                    "ЯНВАРЬ": 1,
                    "ФЕВРАЛЬ": 2,
                    "МАРТ": 3,
                    "АПРЕЛЬ": 4,
                    "МАЙ": 5,
                    "ИЮНЬ": 6,
                    "ИЮЛЬ": 7,
                    "АВГУСТ": 8,
                    "СЕНТЯБРЬ": 9,
                    "ОКТЯБРЬ": 10,
                    "НОЯБРЬ": 11,
                    "ДЕКАБРЬ": 12,
                }

                match = re.search(r"(\w+)\s+(\d+)", day_str)
                if match:
                    month_name, day_num = match.groups()
                    month_num = month_map.get(month_name, 1)
                    return month_num, int(day_num)
                return 1, 1  # Дефолтный результат если не смогли спарсить

            sorted_changes = sorted(
                changes, key=lambda x: parse_date_from_day(x["day"])
            )

            for change in sorted_changes:
                day = change["day"]
                old_val = self.format_schedule_value(change["old_value"])
                new_val = self.format_schedule_value(change["new_value"])

                # Форматируем день в вид: "1.08 ПТ"
                formatted_day = self.format_compact_day(day)

                message += f"{formatted_day} {old_val} → {new_val}\n"

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

    @staticmethod
    def format_compact_day(day_str):
        """Форматирует строку дня в вид типа '1.08 ПТ'.

        Args:
            day_str: Строка дня

        Returns:
            Отформатированная строка дня для уведомления
        """
        # Маппинг месяца к числу
        month_map = {
            "ЯНВАРЬ": "01",
            "ФЕВРАЛЬ": "02",
            "МАРТ": "03",
            "АПРЕЛЬ": "04",
            "МАЙ": "05",
            "ИЮНЬ": "06",
            "ИЮЛЬ": "07",
            "АВГУСТ": "08",
            "СЕНТЯБРЬ": "09",
            "ОКТЯБРЬ": "10",
            "НОЯБРЬ": "11",
            "ДЕКАБРЬ": "12",
        }

        # Маппинг дня недели
        weekday_map = {
            "Пн": "ПН",
            "Вт": "ВТ",
            "Ср": "СР",
            "Чт": "ЧТ",
            "Пт": "ПТ",
            "Сб": "СБ",
            "Вс": "ВС",
        }

        # Парсим строки дней типа "АВГУСТ 24 (Вс)" или "ИЮЛЬ 3 (Чт)"
        match = re.search(r"(\w+)\s+(\d+)\s*\((\w+)\)", day_str)
        if match:
            month_name, day_num, weekday = match.groups()
            month_num = month_map.get(month_name, "01")
            formatted_weekday = weekday_map.get(weekday, weekday.upper())
            return f"{day_num}.{month_num} {formatted_weekday}"

        # Фоллбек на оригинальный формат строки
        return day_str

    @staticmethod
    def format_schedule_value(value) -> str:
        """Форматируем тип дня для уведомления.

        Args:
            value: Оригинальное значение графика на день.

        Returns:
            Форматированное значение графика на день
        """
        if not value.strip() or value == "не назначено":
            return "Выходной"

        match value:
            case "ЛНТС":
                return "🤒 Больничный"
            case "ОТПУСК":
                return "⛱️ Отпуск"
            case "отпуск бс":
                return "⛱️ БС"
            case "Н":
                return "🕵️‍♂️ Отсутствие"
            case "В":
                return "🎖️ Военкомат"
            case _:
                return value

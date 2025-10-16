"""Дополнительные форматтеры для уведомлений и специализированных расписаний.

Модуль предоставляет форматтеры для:
- Уведомлений об изменениях графика
- Расписаний обучений
- График дежурных (экспорт форматирования из парсера)
- График руководителей (экспорт форматирования из парсера)
"""

import re
from datetime import datetime
from typing import Dict, List

from tgbot.misc.helpers import short_name


class ScheduleChangeFormatter:
    """Форматтер для уведомлений об изменениях в графике."""

    @staticmethod
    def format_compact_day(day_str: str) -> str:
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
    def format_schedule_value(value: str) -> str:
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

    @staticmethod
    def format_change_notification(
        fullname: str, changes: List[Dict], current_time
    ) -> str:
        """Форматирует уведомление об изменениях в графике.

        Args:
            fullname: ФИО сотрудника
            changes: Список изменений
            current_time: Текущее время

        Returns:
            Отформатированное сообщение с изменениями
        """
        message = (
            f"🔔 <b>Изменения в графике</b> • {current_time.strftime('%d.%m.%Y')}\n\n"
        )

        # Сортируем изменения по дате (от старых к новым)
        def parse_date_from_day(day_str):
            """Достаем дату из строки дня."""
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

        sorted_changes = sorted(changes, key=lambda x: parse_date_from_day(x["day"]))

        for change in sorted_changes:
            day = change["day"]
            old_val = ScheduleChangeFormatter.format_schedule_value(change["old_value"])
            new_val = ScheduleChangeFormatter.format_schedule_value(change["new_value"])

            # Форматируем день в вид: "1.08 ПТ"
            formatted_day = ScheduleChangeFormatter.format_compact_day(day)

            message += f"{formatted_day} {old_val} → {new_val}\n"

        return message


class StudiesFormatter:
    """Форматтер для расписаний обучений."""

    @staticmethod
    def format_studies_schedule(sessions: List, title: str = "📚 Обучения") -> str:
        """Format study sessions for display.

        Args:
            sessions: Список сессий обучений
            title: Заголовок

        Returns:
            Отформатированный текст расписания обучений
        """
        if not sessions:
            return f"<b>{title}</b>\n\n❌ Не найдено обучений"

        lines = [f"<b>{title}</b>\n"]

        # Group sessions by date
        sessions_by_date = {}
        for session in sessions:
            date_key = session.date.strftime("%d.%m.%Y")
            if date_key not in sessions_by_date:
                sessions_by_date[date_key] = []
            sessions_by_date[date_key].append(session)

        # Sort dates
        sorted_dates = sorted(
            sessions_by_date.keys(), key=lambda x: datetime.strptime(x, "%d.%m.%Y")
        )

        for date_str in sorted_dates:
            date_sessions = sessions_by_date[date_str]
            lines.append(f"📅 <b>{date_str}</b>\n")

            for session in date_sessions:
                lines.append(f"⏰ <b>{session.time}</b> ({session.duration})")
                lines.append(f"📖 {session.title}")

                if session.experience_level:
                    lines.append(f"👥 {session.experience_level}")

                if session.trainer:
                    lines.append(f"🎓 Тренер: {session.trainer}")

                # Show participant count
                if session.participants:
                    present_count = sum(
                        1
                        for _, _, _, attendance, _ in session.participants
                        if attendance == "+"
                    )
                    total_count = len(session.participants)
                    lines.append(f"👤 Участников: {present_count}/{total_count}")

                lines.append("")

        # Remove last empty line
        if lines and lines[-1] == "":
            lines.pop()

        return "\n".join(lines)

    @staticmethod
    def format_user_studies_schedule(
        sessions: List, user_fullname: str, names_match_func
    ) -> str:
        """Format study sessions for specific user.

        Args:
            sessions: Список сессий обучений
            user_fullname: ФИО пользователя
            names_match_func: Функция для сравнения имен

        Returns:
            Отформатированное расписание обучений для пользователя
        """
        if not sessions:
            return "<b>📚 Твои обучения</b>\n\n❌ Не найдено обучений"

        lines = ["<b>📚 Твои обучения</b>\n"]

        # Sort by date
        sorted_sessions = sorted(sessions, key=lambda x: x.date)

        for session in sorted_sessions:
            lines.append(f"📅 <b>{session.date.strftime('%d.%m.%Y')}</b>")
            lines.append(f"⏰ {session.time} ({session.duration})")
            lines.append(f"📖 {session.title}")

            if session.experience_level:
                lines.append(f"👥 {session.experience_level}")

            if session.trainer:
                lines.append(f"🎓 Тренер: {session.trainer}")

            # Show user's attendance status
            for area, name, rg, attendance, reason in session.participants:
                if names_match_func(user_fullname, name):
                    status_icon = (
                        "✅"
                        if attendance == "+"
                        else "❌"
                        if attendance == "-"
                        else "❓"
                    )
                    lines.append(f"{status_icon} Статус: {attendance}")
                    if reason:
                        lines.append(f"📝 Причина: {reason}")
                    break

            lines.append("")

        # Remove last empty line
        if lines and lines[-1] == "":
            lines.pop()

        return "\n".join(lines)

    @staticmethod
    def format_studies_detailed(sessions: List) -> str:
        """Format study sessions with detailed participant information.

        Args:
            sessions: Список сессий обучений

        Returns:
            Детальное расписание обучений
        """
        if not sessions:
            return "<b>📚 Детальное расписание обучений</b>\n\n❌ Не найдено обучений"

        lines = ["<b>📚 Детальное расписание обучений</b>\n"]

        for session in sorted(sessions, key=lambda x: x.date):
            lines.append(f"📅 <b>{session.date.strftime('%d.%m.%Y')}</b>")
            lines.append(f"⏰ {session.time} ({session.duration})")
            lines.append(f"📖 {session.title}")

            if session.experience_level:
                lines.append(f"👥 {session.experience_level}")

            if session.trainer:
                lines.append(f"🎓 Тренер: {session.trainer}")

            lines.append("")
            lines.append("<b>👥 Участники:</b>")

            if session.participants:
                for area, name, rg, attendance, reason in session.participants:
                    status_icon = (
                        "✅"
                        if attendance == "+"
                        else "❌"
                        if attendance == "-"
                        else "❓"
                    )
                    participant_line = f"{status_icon} {short_name(name)} ({area})"
                    if rg:
                        participant_line += f" - РГ: {rg}"
                    if reason:
                        participant_line += f" - {reason}"
                    lines.append(participant_line)
            else:
                lines.append("• Список участников пуст")

            lines.append("")

        # Remove last empty line
        if lines and lines[-1] == "":
            lines.pop()

        return "\n".join(lines)

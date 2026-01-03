"""Геттеры для функций графиков."""

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Sequence

from aiogram import Bot
from aiogram_dialog import DialogManager
from sqlalchemy import func, select
from stp_database.models.Stats.tutors_schedule import TutorsSchedule
from stp_database.models.STP import Employee
from stp_database.repo.Stats import StatsRequestsRepo
from stp_database.repo.STP import MainRequestsRepo

from tgbot.misc.dicts import months_emojis, russian_months, schedule_types
from tgbot.misc.helpers import format_fullname, strftime_date
from tgbot.services.files_processing.formatters.schedule import (
    get_current_date,
    get_current_month,
)
from tgbot.services.files_processing.handlers.schedule import schedule_service
from tgbot.services.files_processing.parsers.schedule import ScheduleParser


async def schedules_getter(
    user: Employee, stp_repo: MainRequestsRepo, **_kwargs
) -> Dict[str, Any]:
    """Геттер для главного меню графиков.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь с доступом сотрудника к бирже
    """
    exchange_banned = await stp_repo.exchange.is_user_exchange_banned(user.user_id)
    tutors_access = True if user.is_tutor or user.role in [2, 3, 10] else False
    return {"exchange_banned": exchange_banned, "tutor_access": tutors_access}


async def user_schedule_getter(
    bot: Bot,
    user: Employee,
    stp_repo: MainRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> Dict[str, Any]:
    """Геттер навигации по месяцам для расписания сотрудника.

    Args:
        bot: Экземпляр бота
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь для смены месяца графика
    """
    current_date_str = dialog_manager.dialog_data.get("current_date")
    if current_date_str is None:
        current_date = get_current_date()
    else:
        current_date = datetime.fromisoformat(current_date_str)

    current_month = dialog_manager.dialog_data.get("current_month", get_current_month())
    current_year = dialog_manager.dialog_data.get("current_year", datetime.now().year)

    month_emoji = months_emojis.get(current_month.lower(), "📅")

    selected_mode = dialog_manager.find("my_schedule_mode").get_checked()
    is_detailed_mode = selected_mode == "detailed"
    button_text = "📋 Кратко" if is_detailed_mode else "📋 Подробнее"

    mode_options = [
        ("compact", "Кратко"),
        ("detailed", "Детально"),
    ]

    schedule_text = await schedule_service.get_user_schedule_response(
        user=user,
        month=current_month,
        year=current_year,
        compact=not is_detailed_mode,
        stp_repo=stp_repo,
        bot=bot,
    )

    # Get schedule file metadata for the selected month/year
    file_name = "Файл не найден"
    upload_date = "Неизвестно"

    try:
        # Query all files and filter for division schedules
        all_files = await stp_repo.upload.get_files()

        # Определяем период (I или II) на основе месяца
        month_to_num = {
            "январь": 1,
            "февраль": 2,
            "март": 3,
            "апрель": 4,
            "май": 5,
            "июнь": 6,
            "июль": 7,
            "август": 8,
            "сентябрь": 9,
            "октябрь": 10,
            "ноябрь": 11,
            "декабрь": 12,
        }
        month_num = month_to_num.get(current_month.lower(), 1)
        period = "I" if month_num <= 6 else "II"

        # Filter files that match schedule pattern for this division, period, and year
        matching_files = []
        for f in all_files:
            if f.file_name:
                # Check if file matches pattern: ГРАФИК {division} {period} {year}.xlsx
                name_parts = f.file_name.split()
                year_part = name_parts[3].split('.')[0] if len(name_parts) >= 4 else ""
                if (
                    len(name_parts) >= 4
                    and name_parts[0] == "ГРАФИК"
                    and name_parts[1] == user.division
                    and name_parts[2].upper() == period
                    and year_part == str(current_year)
                ):
                    matching_files.append(f)

        if matching_files:
            latest_file = matching_files[0]
            file_name = latest_file.file_name or "Неизвестный файл"
            if latest_file.uploaded_at:
                upload_date = latest_file.uploaded_at.strftime(strftime_date)
    except Exception:
        pass

    return {
        "current_month": current_month,
        "month_emoji": month_emoji,
        "month_display": f"{month_emoji} {current_month.capitalize()}",
        "schedule_text": schedule_text,
        "detail_button_text": button_text,
        "is_detailed_mode": is_detailed_mode,
        "mode_options": mode_options,
        "selected_mode": selected_mode,
        "file_name": file_name,
        "upload_date": upload_date,
        "current_time_str": current_date.strftime(strftime_date),
    }


async def duty_schedule_getter(
    user: Employee, stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для получения расписания дежурных.

    Стандартно возвращает расписание на текущий день

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с текстом графика дежурных
    """
    current_date_str = dialog_manager.dialog_data.get("current_date")
    if current_date_str is None:
        current_date = get_current_date()
    else:
        current_date = datetime.fromisoformat(current_date_str)

    duties_text = await schedule_service.get_duties_response(
        division=user.division, date=current_date, stp_repo=stp_repo
    )

    date_display = current_date.strftime("%d.%m")
    is_today = current_date.date() == get_current_date().date()

    # Get latest schedule file metadata
    file_name = "Файл не найден"
    upload_date = "Неизвестно"

    try:
        # Query all files and filter for division schedules
        all_files = await stp_repo.upload.get_files()

        # Filter files that match schedule pattern for this division
        division_pattern = f"ГРАФИК {user.division}"
        matching_files = [
            f
            for f in all_files
            if f.file_name and f.file_name.startswith(division_pattern)
        ]

        if matching_files:
            latest_file = matching_files[0]
            file_name = latest_file.file_name or "Неизвестный файл"
            if latest_file.uploaded_at:
                upload_date = latest_file.uploaded_at.strftime(strftime_date)
    except Exception:
        pass

    return {
        "duties_text": duties_text,
        "date_display": date_display,
        "is_today": is_today,
        "file_name": file_name,
        "upload_date": upload_date,
        "current_time_str": current_date.strftime(strftime_date),
    }


async def head_schedule_getter(
    user: Employee, stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для получения расписания руководителей.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с текстом графика руководителей
    """
    current_date_str = dialog_manager.dialog_data.get("current_date")
    if current_date_str is None:
        current_date = get_current_date()
    else:
        current_date = datetime.fromisoformat(current_date_str)

    heads_text = await schedule_service.get_heads_response(
        division=user.division, date=current_date, stp_repo=stp_repo
    )

    date_display = current_date.strftime("%d.%m")
    is_today = current_date.date() == get_current_date().date()

    # Get latest schedule file metadata
    file_name = "Файл не найден"
    upload_date = "Неизвестно"

    try:
        # Query all files and filter for division schedules
        all_files = await stp_repo.upload.get_files()

        # Filter files that match schedule pattern for this division
        division_pattern = f"ГРАФИК {user.division}"
        matching_files = [
            f
            for f in all_files
            if f.file_name and f.file_name.startswith(division_pattern)
        ]

        if matching_files:
            latest_file = matching_files[0]
            file_name = latest_file.file_name or "Неизвестный файл"
            if latest_file.uploaded_at:
                upload_date = latest_file.uploaded_at.strftime(strftime_date)
    except Exception:
        pass

    return {
        "heads_text": heads_text,
        "date_display": date_display,
        "is_today": is_today,
        "file_name": file_name,
        "upload_date": upload_date,
        "current_time_str": current_date.strftime(strftime_date),
    }


async def tutors_schedule_getter(
    user: Employee,
    stats_repo: StatsRequestsRepo,
    stp_repo: MainRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> Dict[str, Any]:
    """Геттер для получения расписания наставников.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stats_repo: Репозиторий операций с базой Stats
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с текстом графика наставников
    """
    mode_options = [
        ("mine", "Только мое"),
        ("all", "Общее"),
    ]

    current_date_str = dialog_manager.dialog_data.get("current_date")
    if current_date_str is None:
        current_date = get_current_date()
    else:
        current_date = datetime.fromisoformat(current_date_str)

    selected_date = current_date.date()
    today = get_current_date().date()
    is_historical = selected_date != today

    # Получаем выбранный режим отображения
    selected_mode = dialog_manager.find("tutors_schedule_mode").get_checked()

    # Для исторических дат используем кастомный запрос без фильтрации по extraction_period
    # Это позволяет видеть данные, которые были выгружены в прошлом
    if is_historical:
        # Создаем базовый запрос без фильтра extraction_period
        base_query = select(TutorsSchedule).where(
            func.date(TutorsSchedule.training_day) == selected_date
        )

        # Применяем фильтр подразделения
        division_value = "НТП НЦК" if user.division == "НЦК" else user.division
        base_query = base_query.where(TutorsSchedule.tutor_division == division_value)

        # Для режима "Только мое" добавляем фильтр по наставнику
        if selected_mode == "mine":
            base_query = base_query.where(TutorsSchedule.tutor_fullname == user.fullname)

        base_query = base_query.order_by(TutorsSchedule.training_start_time)

        # Выполняем запрос
        result = await stats_repo.session.execute(base_query)
        trainees_schedule: Sequence[TutorsSchedule] = result.scalars().all()

        # Для всех данных (нужны для получения created_at) берем без фильтра по наставнику
        all_query = select(TutorsSchedule).where(
            func.date(TutorsSchedule.training_day) == selected_date
        )
        all_query = all_query.where(TutorsSchedule.tutor_division == division_value)
        all_query = all_query.order_by(TutorsSchedule.training_start_time)

        all_result = await stats_repo.session.execute(all_query)
        all_trainees_schedule: Sequence[TutorsSchedule] = all_result.scalars().all()
    else:
        # Для текущего дня используем существующий метод с фильтрацией по MAX extraction_period
        all_trainees_schedule: Sequence[
            TutorsSchedule
        ] = await stats_repo.tutors_schedule.get_tutor_trainees_by_date(
            training_date=selected_date,
            division=user.division,
        )

        # Затем фильтруем данные в зависимости от выбранного режима
        if selected_mode == "mine":
            trainees_schedule: Sequence[
                TutorsSchedule
            ] = await stats_repo.tutors_schedule.get_tutor_trainees_by_date(
                tutor_fullname=user.fullname,
                training_date=selected_date,
                division=user.division,
            )
        else:
            trainees_schedule = all_trainees_schedule

    # Формируем текст для отображения
    if trainees_schedule:
        tutors_text = (
            f"<b>🎓 Наставничество на {current_date.strftime('%d.%m.%Y')}</b>\n\n"
        )

        # Получаем всех сотрудников для поиска
        all_employees = await stp_repo.employee.get_users()

        # Создаем словарь для быстрого поиска по ФИО
        employees_by_fullname = {emp.fullname: emp for emp in all_employees}

        for i, schedule in enumerate(trainees_schedule, 1):
            # Ищем стажера в базе сотрудников
            trainee_employee = employees_by_fullname.get(schedule.trainee_fullname)
            if trainee_employee:
                formatted_trainee = format_fullname(
                    user=trainee_employee, short=True, gender_emoji=True
                )
            else:
                # Если не нашли в базе, используем имя из расписания
                formatted_trainee = schedule.trainee_fullname

            # Ищем наставника в базе сотрудников
            tutor_employee = (
                employees_by_fullname.get(schedule.tutor_fullname)
                if schedule.tutor_fullname
                else None
            )
            if tutor_employee:
                formatted_tutor = format_fullname(
                    user=tutor_employee, short=True, gender_emoji=True
                )
            elif schedule.tutor_fullname:
                # Если не нашли в базе, используем имя из расписания
                formatted_tutor = schedule.tutor_fullname
            else:
                formatted_tutor = "🎓 Наставник не указан"

            tutors_text += f"<b>Наставник:</b> {formatted_tutor}\n<b>Стажер:</b> {formatted_trainee}\n"

            # Добавляем время обучения
            if not schedule.training_start_time and not schedule.training_end_time:
                time_text = "Неизвестно"
            else:
                start_time = (
                    schedule.training_start_time.strftime("%H:%M")
                    if schedule.training_start_time
                    else "Не указано"
                )
                end_time = (
                    schedule.training_end_time.strftime("%H:%M")
                    if schedule.training_end_time
                    else "Не указано"
                )
                time_text = f"{start_time} - {end_time}"
            tutors_text += f"⏰ <b>Время:</b> {time_text}\n"

            if schedule.trainee_type:
                type_mapping = {
                    1: "До трудоустройства",
                    2: "Основная стажировка",
                    3: "Общий ряд",
                }
                type_text = type_mapping.get(
                    schedule.trainee_type, schedule.trainee_type
                )
                tutors_text += f"📝 <b>Тип:</b> {type_text}\n"
            tutors_text += "\n"
    else:
        # Персонализированное сообщение в зависимости от режима
        if selected_mode == "mine":
            empty_message = "📭 На выбранный день у тебя нет стажеров"
        else:
            empty_message = "📭 На выбранный день стажеров не найдено"

        tutors_text = f"<b>🎓 Наставничество на {current_date.strftime('%d.%m.%Y')}</b>\n\n{empty_message}\n\n"

    # Добавляем информацию о времени создания данных (используем общие данные для получения времени)
    if all_trainees_schedule:
        data_created_at = all_trainees_schedule[0].created_at.strftime(strftime_date)
    else:
        data_created_at = "Неизвестно"

    date_display = current_date.strftime("%d.%m")
    is_today = current_date.date() == get_current_date().date()

    return {
        "tutors_text": tutors_text,
        "date_display": date_display,
        "is_today": is_today,
        "mode_options": mode_options,
        "data_created_at": data_created_at,
        "current_time_str": datetime.now(timezone(timedelta(hours=5))).strftime(strftime_date),
    }


async def group_schedule_getter(
    user: Employee, stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для получения расписания группы сотрудника.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с текстом графика группы сотрудника
    """
    current_date_str = dialog_manager.dialog_data.get("current_date")
    if current_date_str is None:
        current_date = get_current_date()
    else:
        current_date = datetime.fromisoformat(current_date_str)

    (
        group_text,
        total_pages,
        has_prev,
        has_next,
    ) = await schedule_service.get_group_schedule_response(
        user=user,
        date=current_date,
        stp_repo=stp_repo,
        is_head=True if user.role == 2 else False,
    )

    date_display = current_date.strftime("%d.%m")
    is_today = current_date.date() == get_current_date().date()

    # Get latest schedule file metadata
    file_name = "Файл не найден"
    upload_date = "Неизвестно"

    try:
        # Query all files and filter for division schedules
        all_files = await stp_repo.upload.get_files()

        # Filter files that match schedule pattern for this division
        division_pattern = f"ГРАФИК {user.division}"
        matching_files = [
            f
            for f in all_files
            if f.file_name and f.file_name.startswith(division_pattern)
        ]

        if matching_files:
            latest_file = matching_files[0]
            file_name = latest_file.file_name or "Неизвестный файл"
            if latest_file.uploaded_at:
                upload_date = latest_file.uploaded_at.strftime(strftime_date)
    except Exception:
        pass

    return {
        "group_text": group_text,
        "date_display": date_display,
        "is_today": is_today,
        "file_name": file_name,
        "upload_date": upload_date,
        "current_time_str": current_date.strftime(strftime_date),
    }


async def prepare_schedule_calendar_data(
    stp_repo: MainRequestsRepo,
    user: Employee,
    dialog_manager: DialogManager,
    target_month: str = None,
    target_year: int = None,
) -> None:
    """Подготавливает данные календаря для отображения рабочих дней в графике.

    Args:
        stp_repo: Репозиторий операций с базой STP
        user: Пользователь
        dialog_manager: Менеджер диалога
        target_month: Целевой месяц для загрузки (если None, то текущий)
        target_year: Целевой год для загрузки (если None, то текущий)
    """
    try:
        # Получаем календарный виджет
        calendar_widget = dialog_manager.find("my_schedule_calendar")

        # Определяем месяц для загрузки
        if target_month:
            month_name = target_month
        elif calendar_widget:
            current_offset = calendar_widget.get_offset()
            if current_offset:
                month_name = russian_months.get(
                    current_offset.month, get_current_month()
                )
            else:
                month_name = get_current_month()
        else:
            month_name = get_current_month()

        # Определяем год для загрузки
        if target_year:
            year = target_year
        elif calendar_widget:
            current_offset = calendar_widget.get_offset()
            if current_offset:
                year = current_offset.year
            else:
                year = dialog_manager.dialog_data.get(
                    "current_year", datetime.now().year
                )
        else:
            year = dialog_manager.dialog_data.get("current_year", datetime.now().year)

        # Проверяем, не загружали ли мы уже данные для этого месяца и года
        loaded_month = dialog_manager.dialog_data.get("loaded_schedule_month", "")
        loaded_year = dialog_manager.dialog_data.get("loaded_schedule_year", "")
        if loaded_month and loaded_month == month_name and loaded_year == str(year):
            return

        # Очищаем предыдущие данные при смене месяца
        dialog_manager.dialog_data["shift_dates"] = {}

        # Загружаем данные расписания
        parser = ScheduleParser()
        all_shift_dates = {}
        current_date = datetime.now().date()

        try:
            # Получаем расписание с дежурствами (включает в себя базовое расписание)
            schedule_dict = await parser.get_user_schedule_with_duties(
                fullname=user.fullname,
                month=month_name,
                year=year,
                division=user.division,
                stp_repo=stp_repo,
                current_day_only=False,
            )

            if not schedule_dict:
                dialog_manager.dialog_data["shift_dates"] = {}
                dialog_manager.dialog_data["loaded_schedule_month"] = month_name
                dialog_manager.dialog_data["loaded_schedule_year"] = str(year)
                return

            # Получаем номер месяца
            month_to_num = {name.lower(): num for num, name in russian_months.items()}
            month_num = month_to_num.get(month_name.lower())
            if not month_num:
                return

            # Извлекаем рабочие дни
            for day, (schedule, duty_info) in schedule_dict.items():
                if schedule and not any(
                    schedule in schedule_list
                    for schedule_list in schedule_types.values()
                ):
                    # Извлекаем номер дня
                    day_match = re.search(r"(\d{1,2})", day)
                    if day_match:
                        day_num = f"{int(day_match.group(1)):02d}"
                        # Создаем ключ для месяца и дня
                        month_day_key = f"{month_num:02d}_{day_num}"
                        all_shift_dates[month_day_key] = {
                            "schedule": schedule,
                            "duty_info": duty_info,
                            "month": month_num,
                            "day": int(day_num),
                            "year": year,
                        }

                        # Для текущего месяца и года сохраняем также простой ключ
                        if (
                            month_name.lower() == get_current_month().lower()
                            and year == datetime.now().year
                        ):
                            all_shift_dates[day_num] = {
                                "schedule": schedule,
                                "duty_info": duty_info,
                            }

        except Exception:
            all_shift_dates = {}

        # Сохраняем данные в dialog_data
        dialog_manager.dialog_data["shift_dates"] = all_shift_dates
        dialog_manager.dialog_data["loaded_schedule_month"] = month_name
        dialog_manager.dialog_data["loaded_schedule_year"] = str(year)

    except Exception:
        dialog_manager.dialog_data["shift_dates"] = {}


async def my_schedule_calendar_getter(
    user: Employee, stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для календарного вида моего расписания.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с данными для календарного отображения
    """
    # Получаем отображаемый месяц и год из календаря
    calendar_widget = dialog_manager.find("my_schedule_calendar")
    displayed_month_name = get_current_month()
    displayed_year = datetime.now().year

    if calendar_widget:
        try:
            current_offset = calendar_widget.get_offset()
            if current_offset:
                displayed_month_name = russian_months.get(
                    current_offset.month, get_current_month()
                )
                displayed_year = current_offset.year
        except Exception:
            pass

    # Подготавливаем данные календаря для отображения рабочих дней
    # Форсируем перезагрузку данных при каждом вызове геттера
    dialog_manager.dialog_data["loaded_schedule_month"] = ""
    await prepare_schedule_calendar_data(
        stp_repo, user, dialog_manager, displayed_month_name, displayed_year
    )

    month_emoji = months_emojis.get(displayed_month_name.lower(), "📅")

    return {
        "month": displayed_month_name.capitalize(),
        "month_emoji": month_emoji,
        "month_display": f"{month_emoji} {displayed_month_name.capitalize()}",
    }

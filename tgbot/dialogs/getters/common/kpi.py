"""Геттеры показателей и нормативов."""

import datetime
from typing import Any, Dict

from aiogram_dialog import DialogManager
from stp_database.models.KPI.head_premium import HeadPremium
from stp_database.models.KPI.spec_premium import SpecPremium
from stp_database.models.STP import Employee
from stp_database.repo.KPI.requests import KPIRequestsRepo

from tgbot.misc.dicts import months_emojis, russian_months
from tgbot.misc.helpers import strftime_date
from tgbot.services.files_processing.formatters.schedule import get_current_month
from tgbot.services.salary import KPICalculator, SalaryCalculator, SalaryFormatter


def get_extraction_period_from_month(month_name: str) -> datetime.datetime:
    """Получает extraction_period на основе названия месяца.

    Args:
        month_name: Название месяца на русском языке

    Returns:
        datetime для первого дня указанного месяца текущего года
    """
    # Получаем номер месяца из русского названия
    month_to_num = {name: num for num, name in russian_months.items()}
    month_num = month_to_num.get(month_name.lower())

    if not month_num:
        # Если месяц не найден, возвращаем текущий месяц
        return datetime.datetime.today().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

    # Получаем текущий год
    current_year = datetime.datetime.today().year

    return datetime.datetime(
        year=current_year,
        month=month_num,
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


async def base_kpi_data(
    user: Employee,
    kpi_repo: KPIRequestsRepo,
    dialog_manager: DialogManager = None,
    **_kwargs,
) -> Dict[str, Any]:
    """Геттер для получения базовой информации о премии пользователя.

    Args:
        user: Экземпляр пользователя с моделью Employee
        kpi_repo: Репозиторий операций с базой KPI
        dialog_manager: Менеджер диалога для получения выбранного месяца

    Returns:
        Словарь с информацией о премии пользователя
    """
    # Получаем выбранный месяц из dialog_manager или используем текущий
    if dialog_manager:
        current_month = dialog_manager.dialog_data.get(
            "current_month", get_current_month()
        )
    else:
        current_month = get_current_month()

    extraction_period = get_extraction_period_from_month(current_month)

    if user.role == 2:
        premium: HeadPremium = await kpi_repo.head_premium.get_premium(
            user.fullname, extraction_period=extraction_period
        )
    else:
        premium: SpecPremium = await kpi_repo.spec_premium.get_premium(
            user.fullname, extraction_period=extraction_period
        )

    # Получаем month_display для UI
    month_emoji = months_emojis.get(current_month.lower(), "📅")
    month_display = f"{month_emoji} {current_month.capitalize()}"

    return {
        "premium": premium,
        "current_month": current_month,
        "month_display": month_display,
        "extraction_period": extraction_period,
    }


async def kpi_getter(
    user: Employee, kpi_repo: KPIRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для получения показателей KPI сотрудника.

    Args:
        user: Экземпляр пользователя с моделью Employee
        kpi_repo: Репозиторий операций с базой KPI
        dialog_manager: Менеджер диалога для получения выбранного месяца

    Returns:
        Словарь с текстом сообщения о показателях пользователя
    """
    data = await base_kpi_data(user, kpi_repo, dialog_manager, **_kwargs)
    premium = data.get("premium")

    if not premium:
        return {
            "kpi_text": "🌟 <b>Показатели</b>\n\nНе смог найти твои показатели в премиуме :(",
            "month_display": data.get("month_display", "📅 Месяц"),
        }

    # Форматирование даты
    updated_at_str = "—"
    if premium.updated_at:
        updated_at_str = premium.updated_at.strftime(strftime_date)

    current_time_str = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=5))
    ).strftime(strftime_date)

    if user.role == 2:
        kpi_text = f"""🌟 <b>Показатели</b>

🔧 <b>FLR - {SalaryFormatter.format_percentage(premium.flr_premium)}</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.flr)}</blockquote>

⚖️ <b>ГОК - {SalaryFormatter.format_percentage(premium.gok_premium)}</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.gok)}</blockquote>

🎯 <b>Цель - {SalaryFormatter.format_percentage(premium.target_premium)}</b>
<blockquote>Тип: {premium.target_type or "—"}
Факт: {SalaryFormatter.format_value(premium.target)}</blockquote>

💰 <b>Итого:</b>
<b>Общая премия: {SalaryFormatter.format_percentage(premium.total_premium)}</b>

{"📈 Всего чатов: " + SalaryFormatter.format_value(premium.contacts_count) if user.division == "НЦК" else "📈 Всего звонков: " + SalaryFormatter.format_value(premium.contacts_count)}

<i>Выгружено: {updated_at_str}</i>
<i>Обновлено: {datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5))).strftime(strftime_date)}</i>"""

    else:
        contacts_text = (
            f"📈 Всего чатов: {SalaryFormatter.format_value(premium.contacts_count)}"
            if user.division == "НЦК"
            else f"📈 Всего звонков: {SalaryFormatter.format_value(premium.contacts_count)}"
        )

        delay_text = (
            f"⏰ Задержка: {SalaryFormatter.format_value(premium.delay, '%')}"
            if user.division != "НЦК"
            else ""
        )

        kpi_text = f"""🌟 <b>Показатели</b>
    
📊 <b>Оценка клиента - {SalaryFormatter.format_percentage(premium.csi_premium)}</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.csi)}</blockquote>
    
🎯 <b>Отклик</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.csi_response)}</blockquote>
    
🔧 <b>FLR - {SalaryFormatter.format_percentage(premium.flr_premium)}</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.flr)}</blockquote>
    
⚖️ <b>ГОК - {SalaryFormatter.format_percentage(premium.gok_premium)}</b>
<blockquote>Факт: {SalaryFormatter.format_value(premium.gok)}</blockquote>
    
🎯 <b>Цель - {SalaryFormatter.format_percentage(premium.target_premium)}</b>
<blockquote>Тип: {premium.target_type or "—"}
Факт: {SalaryFormatter.format_value(premium.target)}</blockquote>
    
💼 <b>Дополнительно</b>
<blockquote>Дисциплина: {SalaryFormatter.format_percentage(premium.discipline_premium)}
Тестирование: {SalaryFormatter.format_percentage(premium.tests_premium)}
Благодарности: {SalaryFormatter.format_percentage(premium.thanks_premium)}
Наставничество: {SalaryFormatter.format_percentage(premium.tutors_premium)}
Ручная правка: {SalaryFormatter.format_percentage(premium.head_adjust_premium)}</blockquote>
    
💰 <b>Итого:</b>
<b>Общая премия: {SalaryFormatter.format_percentage(premium.total_premium)}</b>
    
{contacts_text}
{delay_text}
<i>Выгружено: {updated_at_str}</i>
<i>Обновлено: {current_time_str}</i>"""

    return {
        "kpi_text": kpi_text,
        "month_display": data.get("month_display", "📅 Месяц"),
    }


async def kpi_requirements_getter(
    user: Employee, kpi_repo: KPIRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для расчета необходимых показателей для выполнения нормативов.

    Args:
        user: Экземпляр пользователя с моделью Employee
        kpi_repo: Репозиторий операций с базой KPI
        dialog_manager: Менеджер диалога для получения выбранного месяца

    Returns:
        Словарь с текстом сообщения о выполнении нормативов пользователем
    """
    data = await base_kpi_data(user, kpi_repo, dialog_manager, **_kwargs)
    premium = data.get("premium")

    if not premium:
        return {
            "requirements_text": """🧮 <b>Нормативы</b>

Не смог найти твои показатели в премиуме :(""",
            "month_display": data.get("month_display", "📅 Месяц"),
        }

    try:
        requirements_text = KPICalculator.format_requirements_message(
            user=user, premium=premium, is_head=True if user.role == 2 else False
        )
    except Exception:
        requirements_text = """🧮 <b>Нормативы</b>
        
Кажется, нормативы пока что не выставлены 🤷‍♂️"""

    return {
        "requirements_text": requirements_text,
        "month_display": data.get("month_display", "📅 Месяц"),
    }


async def salary_getter(
    user: Employee, kpi_repo: KPIRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для расчета заработной платы сотрудника.

    Args:
        user: Экземпляр пользователя с моделью Employee
        kpi_repo: Репозиторий операций с базой KPI
        dialog_manager: Менеджер диалога для получения выбранного месяца

    Returns:
        Словарь с текстом сообщения о зарплате сотрудника
    """
    data = await base_kpi_data(user, kpi_repo, dialog_manager, **_kwargs)
    premium = data.get("premium")

    if not premium:
        return {
            "salary_text": """💰 <b>Зарплата</b>

Не смог найти твои показатели в премиуме :(""",
            "month_display": data.get("month_display", "📅 Месяц"),
        }

    try:
        salary_result = await SalaryCalculator.calculate_salary(
            user=user, premium_data=premium, current_month=data.get("current_month")
        )
    except Exception:
        salary_result = """💰 <b>Зарплата</b>
        
Не смог посчитать твою зарплату 🥺"""

    salary_text = SalaryFormatter.format_salary_message(salary_result, premium)

    return {
        "salary_text": salary_text,
        "month_display": data.get("month_display", "📅 Месяц"),
    }

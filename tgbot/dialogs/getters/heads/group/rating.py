"""Геттеры для просмотра рейтинга группы."""

from typing import Any, Sequence

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import ManagedRadio
from sqlalchemy.orm import Mapped
from stp_database import Employee, MainRequestsRepo
from stp_database.models.KPI.spec_kpi import SpecDayKPI, SpecMonthKPI, SpecWeekKPI
from stp_database.repo.KPI.requests import KPIRequestsRepo

from tgbot.misc.helpers import format_fullname, strftime_date

# Константы для нормативов
NORMATIVES = {
    "csi": "Оценка",
    "pok": "Отклик",
    "flr": "FLR",
    "sales": "Продажи",
}

PERIODS = {
    "day": "День",
    "week": "Неделя",
    "month": "Месяц",
}


async def get_normatives_data(**_kwargs) -> dict[str, Any]:
    """Геттер данных для выбора норматива."""
    return {
        "normatives": [
            (normative_id, normative_name)
            for normative_id, normative_name in NORMATIVES.items()
        ]
    }


async def get_periods_data(**_kwargs) -> dict[str, Any]:
    """Геттер данных для выбора периода."""
    return {
        "periods": [
            (period_id, period_name) for period_id, period_name in PERIODS.items()
        ]
    }


def _get_medal_emoji(position: int) -> str:
    """Получить эмодзи медали для позиции."""
    if position == 1:
        return "🥇"
    elif position == 2:
        return "🥈"
    elif position == 3:
        return "🥉"
    else:
        return f"{position}."


async def _get_kpi_data_by_period(
    kpi_repo: KPIRequestsRepo, fullnames: list[str], period: str
) -> Sequence[SpecDayKPI] | Sequence[SpecWeekKPI] | Sequence[SpecMonthKPI] | list[Any]:
    """Получить KPI данные по периоду."""
    if period == "day":
        return await kpi_repo.spec_day_kpi.get_kpi(fullnames)
    elif period == "week":
        return await kpi_repo.spec_week_kpi.get_kpi(fullnames)
    elif period == "month":
        return await kpi_repo.spec_month_kpi.get_kpi(fullnames)
    return []


def _format_rating_value(value: float | int | None, normative: str) -> str:
    """Форматирование значения норматива для отображения."""
    if value is None:
        return "—"

    if normative == "sales":
        return str(int(value))
    elif normative == "csi":
        return str(value)
    elif normative in ("pok", "flr"):
        return f"{value:.1f}%"
    return str(value)


def _extract_normative_value(
    kpi: SpecDayKPI | SpecWeekKPI | SpecMonthKPI, normative: str
) -> float | None | Mapped[float | None] | Any:
    """Извлекает значение выбранного показателя.

    Args:
        kpi: Выбранный показатель
        normative: Название норматива

    Returns:
        Значение выбранного показателя
    """
    if normative == "csi":
        return kpi.csi
    elif normative == "pok":
        return kpi.pok
    elif normative == "flr":
        return kpi.flr
    elif normative == "sales":
        return float(kpi.sales_count) if kpi.sales_count else None
    return None


def _format_rating_text(
    top_employees: list[dict[str, Any]],
    normative_name: str,
    period_name: str,
    updated_at: str | None,
) -> str:
    """Форматировать текст рейтинга для отображения."""
    lines = []
    lines.append("🎖️ <b>Рейтинг группы</b>\n")
    lines.append(f"📊 <b>Норматив:</b> {normative_name}")
    lines.append(f"📅 <b>Период:</b> {period_name}\n")

    for idx, item in enumerate(top_employees, 1):
        medal = _get_medal_emoji(idx)
        name = item["formatted_name"]
        value = item["formatted_value"]
        contacts = item["contacts_info"]

        lines.append(f"{medal} {name}: <b>{value}</b>")
        if contacts:
            lines.append(contacts)

    if updated_at:
        lines.append(f"\n<i>Обновлено: {updated_at}</i>")

    return "\n".join(lines)


async def get_rating_display_data(
    user: Employee,
    stp_repo: MainRequestsRepo,
    kpi_repo: KPIRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict[str, Any]:
    """Геттер для получения рейтинга участников группы.

    Args:
        user: Руководитель, запросивший рейтинг
        stp_repo: Репозиторий операций с базой STP
        kpi_repo: Репозиторий операций с базой KPI
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с данными рейтинга группы
    """
    period_radio: ManagedRadio = dialog_manager.find("period_radio")
    normative_radio: ManagedRadio = dialog_manager.find("normative_radio")

    period = period_radio.get_checked() or "day"
    normative = normative_radio.get_checked() or "csi"

    base_data = {
        "normatives": [
            (normative_id, normative_name)
            for normative_id, normative_name in NORMATIVES.items()
        ],
        "periods": [
            (period_id, period_name) for period_id, period_name in PERIODS.items()
        ],
        "normative": normative,
        "normative_name": NORMATIVES.get(normative, ""),
        "period": period,
        "period_name": PERIODS.get(period, ""),
        "error": None,
        "top_employees": [],
        "updated_at": None,
    }

    if not user:
        return {
            **base_data,
            "rating_text": "❌ Ошибка: не удалось найти данные руководителя",
        }

    # Получаем всех сотрудников группы руководителя
    team_members = await stp_repo.employee.get_users(head=user.fullname)
    if not team_members:
        return {
            **base_data,
            "rating_text": "❌ В твоей группе нет сотрудников",
        }

    # Получаем ФИО всех сотрудников
    fullnames = [member.fullname for member in team_members]

    # Получаем KPI данные
    kpi_data = await _get_kpi_data_by_period(kpi_repo, fullnames, period)

    # Создаем словарь для быстрого доступа к KPI по ФИО
    kpi_dict = {kpi.fullname: kpi for kpi in kpi_data}

    # Создаем список сотрудников с их показателями
    employees_with_ratings = []
    for member in team_members:
        kpi = kpi_dict.get(member.fullname)
        if kpi:
            value = _extract_normative_value(kpi, normative)
            if value is not None:
                # Добавляем информацию о контактах для контекста
                contacts_info = ""
                if kpi.contacts_count:
                    contacts_info = (
                        f"{kpi.contacts_count} " + "чата(ов)"
                        if user.division == "НЦК"
                        else "звонка(ов)"
                    )

                employees_with_ratings.append({
                    "employee": member,
                    "kpi": kpi,
                    "value": value,
                    "formatted_value": _format_rating_value(value, normative),
                    "formatted_name": format_fullname(
                        member.fullname, True, True, member.username, member.user_id
                    ),
                    "contacts_info": contacts_info,
                })

    if not employees_with_ratings:
        return {
            **base_data,
            "rating_text": f"❌ Нет данных по <code>{NORMATIVES[normative]}</code> за <code>{PERIODS[period].lower()}</code>",
        }

    # Сортируем по значению (по убыванию)
    employees_with_ratings.sort(key=lambda x: x["value"], reverse=True)

    # Ограничиваем топ-10
    top_employees = employees_with_ratings[:10]

    # Получаем время обновления
    updated_at = None
    if top_employees and top_employees[0]["kpi"].updated_at:
        updated_at = top_employees[0]["kpi"].updated_at.strftime(strftime_date)

    # Форматируем текст рейтинга
    rating_text = _format_rating_text(
        top_employees, NORMATIVES[normative], PERIODS[period], updated_at
    )

    return {
        **base_data,
        "rating_text": rating_text,
    }

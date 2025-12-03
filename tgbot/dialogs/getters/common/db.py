"""Геттеры, связанные с базами данных."""

from stp_database.models.STP import Employee
from stp_database.repo.KPI.requests import KPIRequestsRepo
from stp_database.repo.STP import MainRequestsRepo


async def db_getter(
    user: Employee, stp_repo: MainRequestsRepo, kpi_repo: KPIRequestsRepo, **_kwargs
):
    """Геттер для получения базовых данных о сотруднике и репозиториев для взаимодействия с базами данных.

    Данные приходят из DatabaseMiddleware

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        kpi_repo: Репозиторий операций с базой KPI

    Returns:
        Словарь с базовыми данными о сотруднике и репозиториях баз данных
    """
    return {"user": user, "stp_repo": stp_repo, "kpi_repo": kpi_repo}

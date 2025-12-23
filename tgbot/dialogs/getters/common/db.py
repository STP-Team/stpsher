"""Геттеры, связанные с базами данных."""

from stp_database.models.STP import Employee
from stp_database.repo.Stats.requests import StatsRequestsRepo
from stp_database.repo.STP import MainRequestsRepo


async def db_getter(
    user: Employee, stp_repo: MainRequestsRepo, stats_repo: StatsRequestsRepo, **_kwargs
):
    """Геттер для получения базовых данных о сотруднике и репозиториев для взаимодействия с базами данных.

    Данные приходят из DatabaseMiddleware

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        stats_repo: Репозиторий операций с базой KPI

    Returns:
        Словарь с базовыми данными о сотруднике и репозиториях баз данных
    """
    user_tests = await stats_repo.tests.get_tests(employee_fullname=user.fullname)

    return {
        "user": user,
        "stp_repo": stp_repo,
        "stats_repo": stats_repo,
        "have_tests": True if user_tests else False,
    }

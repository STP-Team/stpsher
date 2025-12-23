"""Геттеры, связанные с базами данных."""

from datetime import datetime

from stp_database.models.STP import Employee
from stp_database.repo.Stats.requests import StatsRequestsRepo
from stp_database.repo.STP import MainRequestsRepo

from tgbot.misc.helpers import format_fullname, short_name, strftime_date


async def tests_getter(
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

    for test in user_tests:
        creator = await stp_repo.employee.get_users(fullname=test.creator_fullname)

        if creator:
            test.creator_fullname = format_fullname(creator, True, True)
        else:
            test.creator_fullname = short_name(creator.fullname)

        test.active_from = test.active_from.strftime(strftime_date)

    # Получаем текущее время для отображения времени обновления меню
    current_time = datetime.now()
    current_time_str = current_time.strftime("%d.%m.%Y %H:%M")

    # Время создания данных - используем created_at из первого теста или текущее время, если тестов нет
    if user_tests:
        created_at_str = user_tests[0].created_at.strftime("%d.%m.%Y %H:%M")
    else:
        created_at_str = current_time_str

    return {
        "tests": user_tests,
        "created_at_str": created_at_str,
        "current_time_str": current_time_str,
    }

"""Группы состояний пользователей и дежурных."""

from aiogram.fsm.state import State, StatesGroup


class UserSG(StatesGroup):
    """Группа состояний специалистов и дежурных."""

    # Меню
    menu = State()
    settings = State()

    # Графики
    schedule = State()
    schedule_my = State()
    schedule_my_detailed = State()
    schedule_group = State()
    schedule_duties = State()
    schedule_heads = State()

    # KPI
    kpi = State()
    kpi_requirements = State()
    salary = State()


class Authorization(StatesGroup):
    """Группа состояний для неавторизованных пользователей."""

    email = State()
    auth_code = State()
    fullname = State()

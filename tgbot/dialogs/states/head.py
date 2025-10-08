"""Группы состояний руководителей."""

from aiogram.fsm.state import State, StatesGroup


class HeadSG(StatesGroup):
    """Группа состояний руководителей."""

    # Меню
    menu = State()
    groups = State()
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

    # Моя группа
    my_group = State()

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

    # Активация предметов
    game_products_activation = State()

    # Поиск
    search = State()
    search_specialists = State()
    search_heads = State()
    search_query = State()
    search_result = State()
    search_no_results = State()
    search_user_detail = State()

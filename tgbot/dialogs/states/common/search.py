"""Группы состояний поиска."""

from aiogram.fsm.state import State, StatesGroup


class Search(StatesGroup):
    """Группа состояний поиска."""

    # Меню
    menu = State()

    # Пресеты поиска
    specialists = State()
    heads = State()

    # Поиск по тексту
    query = State()
    query_results = State()
    query_no_results = State()

    # Окно информации о сотруднике
    details_window = State()
    details_access_level_window = State()
    details_schedule_window = State()
    details_kpi_window = State()
    details_kpi_requirements_window = State()
    details_kpi_salary_window = State()
    details_game_achievements = State()
    details_game_products = State()

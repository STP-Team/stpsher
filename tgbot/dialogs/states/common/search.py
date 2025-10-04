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

"""Группы состояний управления группой."""

from aiogram.fsm.state import State, StatesGroup


class HeadGroupSG(StatesGroup):
    """Группа состояний управления группой."""

    # Меню
    menu = State()

    schedule = State()
    rating = State()
    members = State()
    game = State()

    # Game sub-windows
    game_achievements = State()
    game_products = State()
    game_balance_history = State()
    game_casino = State()
    game_rating = State()

    # Member details states (similar to search)
    member_details = State()
    member_schedule = State()
    member_kpi = State()
    member_kpi_requirements = State()
    member_kpi_salary = State()
    member_achievements = State()
    member_inventory = State()
    member_access_level = State()

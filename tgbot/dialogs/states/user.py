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

    # Игра
    game = State()
    game_products = State()
    game_products_activation = State()
    game_activation_detail = State()
    game_activations_empty = State()
    game_achievements = State()
    game_inventory = State()
    game_inventory_detail = State()
    game_history = State()
    game_history_detail = State()

    # Поиск
    search = State()
    search_specialists = State()
    search_heads = State()
    search_query = State()
    search_result = State()
    search_no_results = State()
    search_user_detail = State()

    # Действия
    game_shop_confirm = State()
    game_shop_success = State()

    # Группы
    groups = State()
    groups_list = State()
    groups_list_detail = State()
    groups_cmds = State()
    groups_access = State()
    groups_service_messages = State()
    groups_members = State()
    groups_remove_bot = State()


class Authorization(StatesGroup):
    """Группа состояний для неавторизованных пользователей."""

    email = State()
    auth_code = State()
    fullname = State()

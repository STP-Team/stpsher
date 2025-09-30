from aiogram.fsm.state import State, StatesGroup


class UserSG(StatesGroup):
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

    # Игра
    game = State()
    game_shop = State()
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


class Authorization(StatesGroup):
    email = State()
    auth_code = State()
    fullname = State()

from aiogram.fsm.state import State, StatesGroup


class GokSG(StatesGroup):
    """Группа состояний ГОК."""

    # Меню
    menu = State()
    game = State()
    groups = State()

    # Игра
    game_achievements = State()
    game_products = State()
    game_shop_confirm = State()
    game_shop_success = State()
    game_inventory = State()

    # Активация предметов
    game_products_activation = State()
    game_activation_detail = State()
    game_activations_empty = State()

    # Поиск
    search = State()
    search_specialists = State()
    search_heads = State()
    search_query = State()
    search_result = State()
    search_no_results = State()
    search_user_detail = State()

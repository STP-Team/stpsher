from aiogram.fsm.state import State, StatesGroup


class MipSG(StatesGroup):
    # Меню
    menu = State()
    groups = State()

    # Активация предметов
    products_activation = State()

    # Поиск
    search = State()
    search_specialists = State()
    search_heads = State()
    search_query = State()
    search_result = State()
    search_no_results = State()
    search_user_detail = State()

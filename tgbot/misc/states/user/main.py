from aiogram.fsm.state import State, StatesGroup


class UserSG(StatesGroup):
    menu = State()
    schedule = State()
    kpi = State()
    kpi_requirements = State()
    salary = State()
    game = State()
    game_shop = State()
    game_shop_confirm = State()
    game_shop_success = State()
    game_inventory = State()
    game_inventory_detail = State()
    search = State()
    groups = State()
    settings = State()
    schedule_my = State()
    schedule_my_detailed = State()
    schedule_group = State()
    schedule_duties = State()
    schedule_heads = State()

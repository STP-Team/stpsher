from aiogram.fsm.state import State, StatesGroup


class HeadSearchEmployee(StatesGroup):
    """Состояния для поиска сотрудников руководителем"""

    waiting_search_query = State()  # Ожидание ввода поискового запроса

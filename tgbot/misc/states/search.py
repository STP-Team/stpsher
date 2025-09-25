from aiogram.fsm.state import State, StatesGroup


class SearchEmployee(StatesGroup):
    """Состояния для поиска сотрудников"""

    waiting_search_query = State()


class EditEmployee(StatesGroup):
    """Состояния для редактирования сотрудников (МИП)"""

    waiting_new_fullname = State()

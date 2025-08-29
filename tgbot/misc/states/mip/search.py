from aiogram.fsm.state import State, StatesGroup


class SearchEmployee(StatesGroup):
    """Состояния для поиска сотрудников"""

    waiting_search_query = State()  # Ожидание ввода поискового запроса


class EditEmployee(StatesGroup):
    """Состояния для редактирования данных сотрудника"""

    waiting_new_fullname = State()  # Ожидание ввода нового ФИО

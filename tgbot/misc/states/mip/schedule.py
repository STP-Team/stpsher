from aiogram.fsm.state import State, StatesGroup


class RenameLocalFile(StatesGroup):
    """Состояния для переименования локальных файлов"""

    waiting_new_filename = State()  # Ожидание ввода нового имени файла
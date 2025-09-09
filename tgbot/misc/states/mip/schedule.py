from aiogram.fsm.state import State, StatesGroup


class RenameLocalFile(StatesGroup):
    """Состояния для переименования локальных файлов"""

    waiting_new_filename = State()  # Ожидание ввода нового имени файла


class RecoverFileVersion(StatesGroup):
    """Состояния для восстановления предыдущих версий файлов"""

    selecting_version = State()  # Выбор версии для восстановления
    confirming_restore = State()  # Подтверждение восстановления

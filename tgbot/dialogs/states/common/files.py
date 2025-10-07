"""Группы состояний диалога загрузки файлов."""

from aiogram.fsm.state import State, StatesGroup


class Files(StatesGroup):
    """Группа состояний поиска."""

    # Меню
    menu = State()

    upload = State()  # Загрузка файлов
    history = State()  # История загрузок

    # Локальные файлы
    local = State()
    local_details = State()
    rename = State()
    restore = State()

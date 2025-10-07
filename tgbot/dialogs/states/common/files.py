"""Группы состояний диалога загрузки файлов."""

from aiogram.fsm.state import State, StatesGroup


class Files(StatesGroup):
    """Группа состояний поиска."""

    # Меню
    menu = State()

    # Загрузка файлов
    upload = State()

    # Локальные файлы
    local = State()
    local_details = State()
    rename = State()
    restore = State()

    # История загрузок
    history = State()
    history_details = State()

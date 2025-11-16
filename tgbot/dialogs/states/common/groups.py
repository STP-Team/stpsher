"""Группы состояний для управления группами."""

from aiogram.fsm.state import State, StatesGroup


class Groups(StatesGroup):
    """Группа состояний для управления группами."""

    # Главное меню
    menu = State()

    # Окно групповых команд
    cmds = State()

    # Окна списка групп
    list = State()
    group_details = State()

    # Окна настройки групп
    settings_access = State()
    settings_access_roles = State()
    settings_access_divisions = State()
    settings_access_positions = State()
    settings_services = State()
    settings_members = State()
    settings_remove = State()
    inappropriate_users = State()

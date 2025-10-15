"""Группы состояний root."""

from aiogram.fsm.state import State, StatesGroup


class RootSG(StatesGroup):
    """Группа состояний root."""

    # Меню
    menu = State()
    groups = State()
    settings = State()

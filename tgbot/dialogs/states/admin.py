"""Группы состояний администраторов."""

from aiogram.fsm.state import State, StatesGroup


class AdminSG(StatesGroup):
    """Группа состояний администратора."""

    # Меню
    menu = State()
    groups = State()
    settings = State()

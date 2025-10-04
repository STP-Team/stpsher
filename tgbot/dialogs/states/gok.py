"""Группы состояний ГОК."""

from aiogram.fsm.state import State, StatesGroup


class GokSG(StatesGroup):
    """Группа состояний ГОК."""

    # Меню
    menu = State()

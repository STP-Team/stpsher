"""Группы состояний МИП."""

from aiogram.fsm.state import State, StatesGroup


class MipSG(StatesGroup):
    """Группа состояний МИП."""

    # Меню
    menu = State()

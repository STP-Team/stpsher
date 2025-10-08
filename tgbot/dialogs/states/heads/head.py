"""Группы состояний руководителей."""

from aiogram.fsm.state import State, StatesGroup


class HeadSG(StatesGroup):
    """Группа состояний руководителей."""

    # Меню
    menu = State()
    settings = State()

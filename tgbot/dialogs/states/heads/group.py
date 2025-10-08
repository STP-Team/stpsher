"""Группы состояний управления группой."""

from aiogram.fsm.state import State, StatesGroup


class HeadGroupSG(StatesGroup):
    """Группа состояний управления группой."""

    # Меню
    menu = State()

    schedule = State()
    rating = State()
    members = State()
    game = State()

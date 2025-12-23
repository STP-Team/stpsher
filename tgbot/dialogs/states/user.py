"""Группы состояний пользователей и дежурных."""

from aiogram.fsm.state import State, StatesGroup


class UserSG(StatesGroup):
    """Группа состояний специалистов и дежурных."""

    # Меню
    menu = State()
    horn = State()
    tests = State()
    settings = State()


class Authorization(StatesGroup):
    """Группа состояний для неавторизованных пользователей."""

    email = State()
    auth_code = State()
    fullname = State()

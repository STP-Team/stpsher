"""Группы общих состояний KPI."""

from aiogram.fsm.state import State, StatesGroup


class KPI(StatesGroup):
    """Группа состояний диалога KPI."""

    menu = State()

    requirements = State()  # Расчет планов нормативов
    salary = State()  # Расчет зарплаты

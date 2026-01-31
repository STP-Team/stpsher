"""Группы общих состояний KPI."""

from aiogram.fsm.state import State, StatesGroup


class KpiSG(StatesGroup):
    """Группа состояний диалога KPI."""

    menu = State()

    requirements = State()  # Расчет планов нормативов
    salary = State()  # Расчет зарплаты

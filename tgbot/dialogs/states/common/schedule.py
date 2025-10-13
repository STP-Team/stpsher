"""Группы общих состояний графиков."""

from aiogram.fsm.state import State, StatesGroup


class Schedules(StatesGroup):
    """Группа состояний диалога графиков."""

    menu = State()

    my = State()  # Расчет планов нормативов
    duties = State()  # Расчет зарплаты
    heads = State()  # График дежурных
    group = State()  # График руководителей

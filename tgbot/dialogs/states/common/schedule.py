"""Группы общих состояний графиков."""

from aiogram.fsm.state import State, StatesGroup


class Schedules(StatesGroup):
    """Группа состояний диалога графиков."""

    menu = State()

    my = State()  # Расчет планов нормативов
    duties = State()  # Расчет зарплаты
    heads = State()  # График дежурных
    group = State()  # График руководителей

    # Вид календаря
    duties_calendar = State()  # Календарь для дежурных
    group_calendar = State()  # Календарь для группы
    heads_calendar = State()  # Календарь для руководителей

    # Биржа подмен
    exchanges = State()
    exchange_buy = State()
    exchange_sell = State()
    exchange_my = State()

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

    # Продажа смены - пошаговый процесс
    sell_date_select = State()  # Выбор даты смены
    sell_hours_select = State()  # Выбор часов смены
    sell_time_input = State()  # Ввод времени для частичной смены
    sell_price_input = State()  # Ввод цены
    sell_payment_timing = State()  # Когда платить (сразу/дата)
    sell_payment_date = State()  # Выбор даты платежа (календарь)
    sell_confirmation = State()  # Подтверждение и создание

    # Детальный просмотр обменов
    exchange_buy_detail = State()  # Детали обмена для покупки
    exchange_sell_detail = State()  # Детали собственного обмена для отмены

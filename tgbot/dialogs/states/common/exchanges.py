"""Группы общих состояний биржи подмен."""

from aiogram.fsm.state import State, StatesGroup


class Exchanges(StatesGroup):
    """Группа состояний диалога биржи подмен."""

    menu = State()

    buy = State()
    sell = State()
    my = State()

    # Статистика
    stats = State()

    # Детальный просмотр обменов
    buy_detail = State()  # Детали обмена для покупки
    sell_detail = State()  # Детали собственного обмена для отмены

    # Настройки биржи
    buy_settings = State()
    buy_filters_day = State()
    buy_filters_shift = State()

    sell_settings = State()


class ExchangeCreate(StatesGroup):
    """Группа состояний диалога для создания предложения на бирже подмен."""

    # Общие состояния
    type = State()

    # Состояния для продажи (sell flow)
    date = State()
    shift_type = State()
    hours = State()
    price = State()
    payment_timing = State()
    payment_date = State()
    comment = State()
    confirmation = State()

    # Состояния для покупки (buy flow)
    buy_date = State()
    buy_hours = State()
    buy_price = State()
    buy_comment = State()
    buy_confirmation = State()

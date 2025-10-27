"""Группы общих состояний биржи подмен."""

from aiogram.fsm.state import State, StatesGroup


class Exchanges(StatesGroup):
    """Группа состояний диалога биржи подмен."""

    menu = State()

    buy = State()
    sell = State()
    create = State()
    my = State()

    # Статистика
    stats = State()

    # Детальный просмотр обменов
    buy_detail = State()  # Детали обмена для покупки
    sell_detail = State()  # Детали собственного обмена для отмены
    my_detail = State()  # Детали собственных обменов из раздела "Мои сделки"

    # Настройки биржи
    buy_settings = State()
    buy_filters_day = State()
    buy_filters_shift = State()

    sell_settings = State()


class ExchangeCreateSell(StatesGroup):
    """Группа состояний диалога для создания продажи на бирже."""

    date = State()
    shift_type = State()
    hours = State()
    price = State()
    payment_timing = State()
    payment_date = State()
    comment = State()
    confirmation = State()


class ExchangeCreateBuy(StatesGroup):
    """Группа состояний диалога для создания покупки на бирже."""

    date = State()
    hours = State()
    price = State()
    comment = State()
    confirmation = State()

"""Группы общих состояний биржи подмен."""

from aiogram.fsm.state import State, StatesGroup


class Exchanges(StatesGroup):
    """Группа состояний диалога биржи подмен."""

    menu = State()

    buy = State()
    sell = State()
    my = State()

    # Продажа смены - пошаговый процесс
    sell_date_select = State()  # Выбор даты смены
    sell_hours_select = State()  # Выбор часов смены
    sell_time_input = State()  # Ввод времени для частичной смены
    sell_price_input = State()  # Ввод цены
    sell_payment_timing = State()  # Когда платить (сразу/дата)
    sell_payment_date = State()  # Выбор даты платежа (календарь)
    sell_confirmation = State()  # Подтверждение и создание

    # Детальный просмотр обменов
    buy_detail = State()  # Детали обмена для покупки
    sell_detail = State()  # Детали собственного обмена для отмены

    # Настройки биржи
    buy_settings = State()
    buy_filters_day = State()
    buy_filters_shift = State()

    sell_settings = State()

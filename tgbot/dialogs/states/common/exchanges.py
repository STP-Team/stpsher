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
    finances = State()
    partners = State()

    # Детальный просмотр обменов
    buy_detail = State()  # Детали обмена для покупки
    sell_detail = State()  # Детали собственного обмена для отмены
    my_detail = State()  # Детали собственных обменов из раздела "Мои сделки"

    # Покупка со временем выбора
    buy_time_selection = State()  # Выбор времени для покупки
    buy_confirmation = State()  # Подтверждение покупки с расчетом цены

    # Продажа в ответ на запрос покупки
    sell_time_selection = State()  # Выбор времени для продажи в ответ на buy request
    sell_confirmation = State()  # Подтверждение предложения продажи

    # Настройки биржи
    buy_settings = State()
    buy_filters_day = State()
    buy_filters_shift = State()

    sell_settings = State()
    sell_filters_day = State()
    sell_filters_shift = State()

    # Изменение сделки
    edit_offer = State()
    edit_offer_price = State()
    edit_offer_payment_timing = State()
    edit_offer_payment_date = State()
    edit_offer_comment = State()


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


class ExchangesSub(StatesGroup):
    """Группа состояний диалога для управления подписками на обмены."""

    menu = State()  # Список подписок пользователя
    sub_detail = State()  # Детали конкретной подписки

    create_type = State()  # Выбор типа обменов (sell/buy)
    create_criteria = State()  # Настройка критериев
    create_price = State()  # Настройка цены
    create_time = State()  # Настройка времени
    create_date = State()  # Настройка дат
    create_seller = State()  # Поиск продавца
    create_seller_results = State()  # Результаты поиска продавца
    create_name = State()  # Название подписки
    create_confirmation = State()  # Подтверждение создания


class ExchangesStats(StatesGroup):
    """Группа состояний диалога для просмотра статистики сделок."""

    menu = State()
    finances = State()

"""Группы состояний для управления группами."""

from aiogram.fsm.state import State, StatesGroup


class Game(StatesGroup):
    """Группа состояний для управления игровым профилем."""

    # Меню
    menu = State()

    # Окна достижений
    achievements = State()

    # Окно предметов
    products = State()
    products_confirm = State()
    products_success = State()

    # Окно активаций
    activations = State()
    no_activations = State()
    activation_details = State()

    # Казино
    casino = State()
    casino_slots = State()
    casino_dice = State()
    casino_darts = State()
    casino_bowling = State()
    casino_waiting = State()
    casino_result = State()

    # Инвентарь
    inventory = State()
    inventory_details = State()
    inventory_activation_comment = State()

    # История баланса
    history = State()
    history_details = State()

    # Комментарии менеджера
    activation_approve_comment = State()
    activation_reject_comment = State()

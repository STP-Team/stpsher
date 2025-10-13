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

    # Инвентарь
    inventory = State()
    inventory_details = State()

    # История баланса
    history = State()
    history_details = State()

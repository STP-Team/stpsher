from aiogram.fsm.state import State, StatesGroup


class BroadcastState(StatesGroup):
    """Состояния для процесса рассылки"""

    waiting_message = State()  # Ожидание сообщения от пользователя
    selecting_type = State()  # Выбор типа рассылки (всем/подразделение/группы)
    confirming = State()  # Подтверждение рассылки

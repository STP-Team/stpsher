"""Группы состояний для управления рассылками."""

from aiogram.fsm.state import State, StatesGroup


class Broadcast(StatesGroup):
    """Группа состояний для диалога рассылки."""

    menu = State()

    new_broadcast = State()
    new_broadcast_select = State()
    new_broadcast_text = State()
    new_broadcast_check = State()
    new_broadcast_progress = State()
    new_broadcast_result = State()

    history = State()
    history_detail = State()

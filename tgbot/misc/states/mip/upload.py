from aiogram.fsm.state import State, StatesGroup


class UploadFile(StatesGroup):
    file = State()

from aiogram.fsm.state import State, StatesGroup


class Authorization(StatesGroup):
    email = State()
    auth_code = State()
    fullname = State()

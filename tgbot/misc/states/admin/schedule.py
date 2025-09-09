from aiogram.fsm.state import State, StatesGroup


class RenameLocalFile(StatesGroup):
    waiting_new_filename = State()

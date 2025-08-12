import os

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from tgbot.filters.role import MipFilter
from tgbot.keyboards.mip.schedule.main import ScheduleMenu

mip_list_router = Router()
mip_list_router.message.filter(F.chat.type == "private", MipFilter())
mip_list_router.callback_query.filter(F.message.chat.type == "private", MipFilter())


@mip_list_router.callback_query(ScheduleMenu.filter(F.menu == "list"))
async def upload_menu(callback: CallbackQuery, state: FSMContext):
    files = next(os.walk("uploads"), (None, None, []))[2]

    numbered_files = "\n".join(f"{i}. {file}" for i, file in enumerate(files, 1))

    await callback.message.edit_text(f"""<b>📂 Текущие файлы</b>

{numbered_files}""")

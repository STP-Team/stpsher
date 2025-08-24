from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from tgbot.filters.role import MipFilter
from tgbot.keyboards.mip.schedule.main import schedule_kb
from tgbot.keyboards.user.main import MainMenu

mip_schedule_router = Router()
mip_schedule_router.message.filter(F.chat.type == "private", MipFilter())
mip_schedule_router.callback_query.filter(F.message.chat.type == "private", MipFilter())


@mip_schedule_router.callback_query(MainMenu.filter(F.menu == "schedule"))
async def schedule_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        """📅 Меню графиков""",
        reply_markup=schedule_kb(),
    )

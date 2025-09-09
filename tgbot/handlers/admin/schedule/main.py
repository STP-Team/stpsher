from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from tgbot.filters.role import AdministratorFilter
from tgbot.keyboards.admin.schedule.main import schedule_kb
from tgbot.keyboards.user.main import MainMenu

admin_schedule_router = Router()
admin_schedule_router.message.filter(F.chat.type == "private", AdministratorFilter())
admin_schedule_router.callback_query.filter(
    F.message.chat.type == "private", AdministratorFilter()
)


@admin_schedule_router.callback_query(MainMenu.filter(F.menu == "schedule"))
async def schedule_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        """<b>📅 Меню графиков</b>

Здесь ты найдешь все, что связано с графиками""",
        reply_markup=schedule_kb(),
    )

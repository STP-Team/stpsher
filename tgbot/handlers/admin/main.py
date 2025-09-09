from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models import Employee
from tgbot.filters.role import AdministratorFilter
from tgbot.keyboards.admin.main import main_kb
from tgbot.keyboards.user.main import MainMenu

admin_router = Router()
admin_router.message.filter(F.chat.type == "private", AdministratorFilter())
admin_router.callback_query.filter(
    F.message.chat.type == "private", AdministratorFilter()
)


@admin_router.message(CommandStart())
async def admin_start_cmd(message: Message, user: Employee):
    await message.answer(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

Здесь ты можешь загружать графики, обучения, а так же искать сотрудников и изменять учетки сотрудников""",
        reply_markup=main_kb(),
    )


@admin_router.callback_query(MainMenu.filter(F.menu == "main"))
async def admin_start_cb(callback: CallbackQuery, user: Employee):
    await callback.message.edit_text(
        f"""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

Здесь ты можешь загружать графики, обучения, а так же искать сотрудников и изменять учетки сотрудников""",
        reply_markup=main_kb(),
    )

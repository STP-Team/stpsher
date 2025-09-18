from aiogram import F, Router
from aiogram.types import CallbackQuery

from tgbot.filters.role import HeadFilter
from tgbot.keyboards.head.group.main import group_management_kb
from tgbot.keyboards.user.main import MainMenu

head_group_router = Router()
head_group_router.message.filter(F.chat.type == "private", HeadFilter())
head_group_router.callback_query.filter(F.message.chat.type == "private", HeadFilter())


@head_group_router.callback_query(MainMenu.filter(F.menu == "group_management"))
async def group_management_cb(callback: CallbackQuery):
    """Обработчик управления группой"""
    await callback.message.edit_text(
        """❤️ <b>Группа</b>

Используй меню для выбора действия""",
        reply_markup=group_management_kb(),
    )

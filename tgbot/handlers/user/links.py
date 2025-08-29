from aiogram import F, Router
from aiogram.types import CallbackQuery

from tgbot.keyboards.user.main import MainMenu

user_links_router = Router()
user_links_router.message.filter(F.chat.type == "private")
user_links_router.callback_query.filter(F.message.chat.type == "private")


@user_links_router.callback_query(MainMenu.filter(F.menu == "links"))
async def user_links_cb(callback: CallbackQuery):
    await callback.answer(
        """🚧 Функционал пока недоступен

Вернись через недельку 🧐""",
        show_alert=True,
    )

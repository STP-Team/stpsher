import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from tgbot.keyboards.user.leveling.achievements import achievements_kb
from tgbot.keyboards.user.main import MainMenu

user_leveling_achievements_router = Router()
user_leveling_achievements_router.message.filter(
    F.chat.type == "private",
)
user_leveling_achievements_router.callback_query.filter(
    F.message.chat.type == "private"
)

logger = logging.getLogger(__name__)


@user_leveling_achievements_router.callback_query(
    MainMenu.filter(F.menu == "achievements")
)
async def user_achievements_cb(callback: CallbackQuery):
    await callback.message.edit_text(
        """<b>🎯 Достижения</b>

Здесь ты можешь найти свои, а так же все возможные достижения

<i>За достижения ты получаешь баллы
Их можно тратить на <b>👏 Награды</b></i>""",
        reply_markup=achievements_kb(),
    )

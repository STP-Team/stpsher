import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from tgbot.keyboards.mip.leveling.main import LevelingMenu
from tgbot.keyboards.user.leveling.main import achievements_kb

user_leveling_achievements_router = Router()
user_leveling_achievements_router.message.filter(
    F.chat.type == "private",
)
user_leveling_achievements_router.callback_query.filter(
    F.message.chat.type == "private"
)

logger = logging.getLogger(__name__)


@user_leveling_achievements_router.callback_query(
    LevelingMenu.filter(F.menu == "achievements")
)
async def user_achievements_cb(callback: CallbackQuery):
    await callback.message.edit_text(
        """<b>🎯 Достижения</b>

Здесь ты можешь найти свои, а так же все возможные достижения""",
        reply_markup=achievements_kb(),
    )

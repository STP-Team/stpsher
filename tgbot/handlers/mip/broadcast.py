from aiogram import F, Router
from aiogram.types import CallbackQuery

from tgbot.filters.role import MipFilter
from tgbot.keyboards.mip.broadcast import broadcast_kb
from tgbot.keyboards.user.main import MainMenu

mip_broadcast_router = Router()
mip_broadcast_router.message.filter(F.chat.type == "private", MipFilter())
mip_broadcast_router.callback_query.filter(
    F.message.chat.type == "private", MipFilter()
)


@mip_broadcast_router.callback_query(MainMenu.filter(F.menu == "broadcast"))
async def mip_broadcast_cmd(callback: CallbackQuery):
    await callback.message.edit_text(
        """<b>📢 Рассылка</b>

Здесь ты можешь запустить рассылку сообщений по направлению

<i>Используй меню, чтобы выбрать действие</i>""",
        reply_markup=broadcast_kb(),
    )

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.deep_linking import create_startgroup_link

from tgbot.keyboards.group.main import groups_kb
from tgbot.keyboards.user.main import MainMenu

logger = logging.getLogger(__name__)

group_main_router = Router()
group_main_router.message.filter(F.chat.type == "private")
group_main_router.callback_query.filter(F.message.chat.type == "private")


@group_main_router.callback_query(MainMenu.filter(F.menu == "groups"))
async def group_main_cb(callback: CallbackQuery):
    group_link = await create_startgroup_link(callback.bot, payload="start")
    await callback.message.edit_text(
        """👯‍♀️ <b>Группы</b>

Ты можешь использовать меня для менеджмента групп

🪄 <b>Я умею</b>
∙ Приветствовать новых пользователей
∙ Удалять уволенных
∙ Разрешать доступ к группе конкретных должностям
∙ Удалять сервисные сообщения
∙ Управлять доступом к казино в группе
∙ Просматривать список участников""",
        reply_markup=groups_kb(group_link),
    )

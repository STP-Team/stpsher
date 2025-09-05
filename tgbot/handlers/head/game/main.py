import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from tgbot.filters.role import HeadFilter
from tgbot.keyboards.head.game.main import head_game_kb
from tgbot.keyboards.head.group.main import GroupManagementMenu

head_game_router = Router()
head_game_router.callback_query.filter(F.message.chat.type == "private", HeadFilter())

logger = logging.getLogger(__name__)


@head_game_router.callback_query(GroupManagementMenu.filter(F.menu == "game"))
async def head_game_menu(callback: CallbackQuery):
    """
    Обработчик игрового меню для руководителей
    """
    await callback.message.edit_text(
        """🏮 <b>Игра</b>

Здесь ты можешь:
• Просматривать список всех достижений
• Просматривать список всех предметов""",
        reply_markup=head_game_kb(),
    )
    logger.info(
        f"[Руководитель] - [Игровые достижения] {callback.from_user.username} ({callback.from_user.id}): Открыто меню игровых достижений группы"
    )

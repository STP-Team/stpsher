import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import MipFilter
from tgbot.handlers.user.game.achievements import achievements_all
from tgbot.keyboards.mip.game.main import (
    FilterToggleMenu,
    GameMenu,
    game_kb,
    toggle_filter,
)
from tgbot.keyboards.user.main import MainMenu

mip_game_router = Router()
mip_game_router.message.filter(F.chat.type == "private", MipFilter())
mip_game_router.callback_query.filter(F.message.chat.type == "private", MipFilter())

logger = logging.getLogger(__name__)


@mip_game_router.callback_query(MainMenu.filter(F.menu == "game"))
async def mip_achievements_cmd(callback: CallbackQuery):
    await callback.message.edit_text(
        """<b>🏆 Ачивки</b>

Здесь ты можешь:
- Подтверждать/отклонять покупки специалистов
- Просматривать список достижений
- Просматривать список предметов""",
        reply_markup=game_kb(),
    )


@mip_game_router.callback_query(FilterToggleMenu.filter())
async def toggle_filter_handler(
    callback: CallbackQuery, callback_data: FilterToggleMenu, stp_repo: MainRequestsRepo
):
    """Обработчик переключения фильтров"""
    menu = callback_data.menu
    filter_name = callback_data.filter_name
    current_filters = callback_data.current_filters

    # Переключаем фильтр
    new_filters = toggle_filter(current_filters, filter_name)

    # Переходим на первую страницу при изменении фильтров
    if menu == "achievements_all":
        await achievements_all(
            callback,
            GameMenu(menu="achievements_all", page=1, filters=new_filters),
            stp_repo,
        )

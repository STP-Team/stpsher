import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import MipFilter
from tgbot.handlers.user.leveling.achievements import achievements_all
from tgbot.handlers.user.leveling.awards import awards_all
from tgbot.keyboards.mip.leveling.main import (
    AwardsMenu,
    FilterToggleMenu,
    LevelingMenu,
    leveling_kb,
    toggle_filter,
)
from tgbot.keyboards.user.main import MainMenu

mip_leveling_router = Router()
mip_leveling_router.message.filter(F.chat.type == "private", MipFilter())
mip_leveling_router.callback_query.filter(F.message.chat.type == "private", MipFilter())

logger = logging.getLogger(__name__)


def filter_items_by_division(items, active_filters):
    """Filter achievements or awards by division based on active filters"""
    # Filter by specific divisions
    filtered_items = []
    for item in items:
        if item.division in active_filters:
            filtered_items.append(item)

    return filtered_items


@mip_leveling_router.callback_query(MainMenu.filter(F.menu == "leveling"))
async def mip_achievements_cmd(callback: CallbackQuery):
    await callback.message.edit_text(
        """<b>🏆 Ачивки</b>

Здесь ты можешь:
- Подтверждать/отклонять награды специалистов
- Просматривать список достижений
- Просматривать список наград""",
        reply_markup=leveling_kb(),
    )


@mip_leveling_router.callback_query(FilterToggleMenu.filter())
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
            LevelingMenu(menu="achievements_all", page=1, filters=new_filters),
            stp_repo,
        )
    elif menu == "awards_all":
        await awards_all(
            callback,
            AwardsMenu(menu="awards_all", page=1, filters=new_filters),
            stp_repo,
        )

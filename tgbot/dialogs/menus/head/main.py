"""Генерация диалога для руководителей."""

import logging
from typing import Any

from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import ManagedRadio, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.getters.common.db import db_getter
from tgbot.dialogs.menus.head.kpi import (
    kpi_requirements_window,
    kpi_window,
    salary_window,
)
from tgbot.dialogs.menus.head.schedule import (
    schedule_duties_window,
    schedule_group_window,
    schedule_heads_window,
    schedule_my_window,
    schedule_window,
)
from tgbot.dialogs.menus.head.search import (
    head_search_heads_window,
    head_search_no_results_window,
    head_search_query_window,
    head_search_results_window,
    head_search_specialists_window,
    head_search_user_info_window,
    head_search_window,
)
from tgbot.misc.states.dialogs.head import HeadSG

logger = logging.getLogger(__name__)


menu_window = Window(
    Format("""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

<i>Используй меню для взаимодействия с ботом</i>"""),
    Row(
        SwitchTo(Const("📅 Графики"), id="schedules", state=HeadSG.schedule),
        SwitchTo(Const("🌟 Показатели"), id="kpi", state=HeadSG.kpi),
    ),
    SwitchTo(Const("❤️ Моя группа"), id="my_group", state=HeadSG.my_group),
    SwitchTo(
        Const("✍️ Активация предметов"),
        id="products_activation",
        state=HeadSG.game_products_activation,
    ),
    Row(
        SwitchTo(Const("🕵🏻 Поиск сотрудника"), id="search", state=HeadSG.search),
        SwitchTo(Const("👯‍♀️ Группы"), id="groups", state=HeadSG.groups),
    ),
    state=HeadSG.menu,
)


async def on_start(_start_data: Any, dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _start_data: Дополнительные параметры запуска диалога
        dialog_manager: Менеджер диалога
    """
    try:
        # Стандартный режим отображения графика на "Кратко"
        schedule_mode: ManagedRadio = dialog_manager.find("schedule_mode")
        await schedule_mode.set_checked("compact")

        # TODO вернуть при добавлении игрового меню
        # # Фильтр достижений по должностям на "Все"
        # achievement_division_filter: ManagedRadio = dialog_manager.find(
        #     "achievement_division_filter"
        # )
        # await achievement_division_filter.set_checked("all")
        #
        # # Фильтр достижений по периоду начисления на "Все"
        # achievement_period_filter: ManagedRadio = dialog_manager.find(
        #     "achievement_period_filter"
        # )
        # await achievement_period_filter.set_checked("all")

        # Фильтр поиска по направлению на "Все"
        search_divisions: ManagedRadio = dialog_manager.find("search_divisions")
        await search_divisions.set_checked("all")
    except Exception as e:
        logger.error(f"[Диалоги] Ошибка установки стандартных значений диалога: {e}")


head_dialog = Dialog(
    menu_window,
    schedule_window,
    schedule_my_window,
    schedule_duties_window,
    schedule_group_window,
    schedule_heads_window,
    kpi_window,
    kpi_requirements_window,
    salary_window,
    head_search_window,
    head_search_specialists_window,
    head_search_heads_window,
    head_search_query_window,
    head_search_results_window,
    head_search_no_results_window,
    head_search_user_info_window,
    on_start=on_start,
    getter=db_getter,
)

"""Генерация диалога для специалистов."""

from typing import Any

from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import Button, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.events.common.groups import start_groups_dialog
from tgbot.dialogs.events.common.search import start_search_dialog
from tgbot.dialogs.getters.common.db import db_getter
from tgbot.dialogs.menus.user.game.achievements import game_achievements_window
from tgbot.dialogs.menus.user.game.activations import (
    game_activation_detail_window,
    game_activations_empty_window,
    game_activations_window,
)
from tgbot.dialogs.menus.user.game.game import (
    game_window,
)
from tgbot.dialogs.menus.user.game.history import (
    game_gistory_detail_window,
    game_history_window,
)
from tgbot.dialogs.menus.user.game.inventory import (
    game_inventory_detail_window,
    game_inventory_window,
)
from tgbot.dialogs.menus.user.game.shop import (
    game_shop_confirm_window,
    game_shop_success_window,
    game_shop_window,
)
from tgbot.dialogs.menus.user.kpi import (
    kpi_requirements_window,
    kpi_salary_window,
    kpi_window,
)
from tgbot.dialogs.menus.user.schedule import (
    schedule_duties_window,
    schedule_group_window,
    schedule_heads_window,
    schedule_my_window,
    schedule_window,
)
from tgbot.dialogs.states.user import UserSG

menu_window = Window(
    Format("""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

<i>Используй меню для взаимодействия с ботом</i>"""),
    Row(
        SwitchTo(Const("📅 Графики"), id="schedules", state=UserSG.schedule),
        SwitchTo(Const("🌟 Показатели"), id="kpi", state=UserSG.kpi),
    ),
    SwitchTo(Const("🏮 Игра"), id="game", state=UserSG.game),
    Row(
        Button(Const("🕵🏻 Поиск сотрудника"), id="search", on_click=start_search_dialog),
        Button(Const("👯‍♀️ Группы"), id="groups", on_click=start_groups_dialog),
    ),
    state=UserSG.menu,
)


async def on_start(_on_start: Any, dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        dialog_manager: Менеджер диалога
    """
    # # Стандартный режим отображения графика на "Кратко"
    # schedule_mode: ManagedRadio = dialog_manager.find("schedule_mode")
    # await schedule_mode.set_checked("compact")
    #
    # # Фильтр предметов магазина на "Доступные"
    # product_filter: ManagedRadio = dialog_manager.find("product_filter")
    # await product_filter.set_checked("available")
    #
    # # Фильтр инвентаря на "Все"
    # inventory_filter: ManagedRadio = dialog_manager.find("inventory_filter")
    # await inventory_filter.set_checked("all")
    #
    # # Фильтр достижений по должностям на "Все"
    # achievement_position_filter: ManagedRadio = dialog_manager.find(
    #     "achievement_position_filter"
    # )
    # await achievement_position_filter.set_checked("all")
    #
    # # Фильтр достижений по периоду начисления на "Все"
    # achievement_period_filter: ManagedRadio = dialog_manager.find(
    #     "achievement_period_filter"
    # )
    # await achievement_period_filter.set_checked("all")
    #
    # # Фильтр истории баланса по типу операции на "Все"
    # history_type_filter: ManagedRadio = dialog_manager.find("history_type_filter")
    # await history_type_filter.set_checked("all")
    #
    # # Фильтр истории баланса по источнику операции на "Все"
    # history_source_filter: ManagedRadio = dialog_manager.find("history_source_filter")
    # await history_source_filter.set_checked("all")

    # Фильтр поиска по направлению на "Все"
    # search_divisions: ManagedRadio = dialog_manager.find("search_divisions")
    # await search_divisions.set_checked("all")
    #
    # # Фильтр групповых команд на "Пользователь"
    # groups_cmds_filter: ManagedRadio = dialog_manager.find("groups_cmds_filter")
    # await groups_cmds_filter.set_checked("user")


user_dialog = Dialog(
    menu_window,
    schedule_window,
    schedule_my_window,
    schedule_duties_window,
    schedule_group_window,
    schedule_heads_window,
    kpi_window,
    kpi_requirements_window,
    kpi_salary_window,
    game_window,
    game_activations_window,
    game_activation_detail_window,
    game_activations_empty_window,
    game_shop_window,
    game_shop_confirm_window,
    game_shop_success_window,
    game_inventory_window,
    game_inventory_detail_window,
    game_achievements_window,
    game_history_window,
    game_gistory_detail_window,
    on_start=on_start,
    getter=db_getter,
)

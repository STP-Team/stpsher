from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import ManagedRadio, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

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
    schedule_my_detailed_window,
    schedule_my_window,
    schedule_window,
)
from tgbot.dialogs.menus.user.search import (
    search_heads_window,
    search_no_results_window,
    search_query_window,
    search_results_window,
    search_specialists_window,
    search_user_info_window,
    search_window,
)
from tgbot.misc.states.dialogs.user import UserSG

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
        SwitchTo(Const("🕵🏻 Поиск сотрудника"), id="search", state=UserSG.search),
        SwitchTo(Const("👯‍♀️ Группы"), id="groups", state=UserSG.groups),
    ),
    getter=db_getter,
    state=UserSG.menu,
)


async def on_start(start_data, manager: DialogManager, **kwargs):
    """Установка значений по умолчанию при запуске диалога"""
    # Устанавливаем значение по умолчанию для фильтра магазина
    schedule_mode: ManagedRadio = manager.find("schedule_mode")
    await schedule_mode.set_checked("compact")

    shop_filter: ManagedRadio = manager.find("shop_filter")
    await shop_filter.set_checked("available")

    inventory_filter: ManagedRadio = manager.find("inventory_filter")
    await inventory_filter.set_checked("all")

    achievement_position_filter: ManagedRadio = manager.find(
        "achievement_position_filter"
    )
    await achievement_position_filter.set_checked("all")

    achievement_period_filter: ManagedRadio = manager.find("achievement_period_filter")
    await achievement_period_filter.set_checked("all")

    history_type_filter: ManagedRadio = manager.find("history_type_filter")
    await history_type_filter.set_checked("all")

    history_source_filter: ManagedRadio = manager.find("history_source_filter")
    await history_source_filter.set_checked("all")

    search_divisions: ManagedRadio = manager.find("search_divisions")
    await search_divisions.set_checked("all")


user_dialog = Dialog(
    menu_window,
    schedule_window,
    schedule_my_window,
    schedule_my_detailed_window,
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
    search_window,
    search_specialists_window,
    search_heads_window,
    search_query_window,
    search_results_window,
    search_no_results_window,
    search_user_info_window,
    on_start=on_start,
    getter=db_getter,
)

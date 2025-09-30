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
    schedule_my_detailed_window,
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
    getter=db_getter,
    state=HeadSG.menu,
)


async def on_start(start_data, manager: DialogManager, **kwargs):
    """Установка значений по умолчанию при запуске диалога"""
    # Устанавливаем значение по умолчанию для фильтра магазина
    schedule_mode: ManagedRadio = manager.find("mode_selector")
    await schedule_mode.set_checked("compact")

    achievement_position_filter: ManagedRadio = manager.find(
        "achievement_position_filter"
    )
    await achievement_position_filter.set_checked("all")

    achievement_period_filter: ManagedRadio = manager.find("achievement_period_filter")
    await achievement_period_filter.set_checked("all")

    search_divisions: ManagedRadio = manager.find("search_divisions")
    await search_divisions.set_checked("all")


head_dialog = Dialog(
    menu_window,
    schedule_window,
    schedule_my_window,
    schedule_my_detailed_window,
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

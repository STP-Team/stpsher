from aiogram_dialog import Dialog
from aiogram_dialog.widgets.kbd import Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.getters.common.db import db_getter
from tgbot.dialogs.menus.head.kpi import (
    kpi_requirements_window,
    kpi_window,
    salary_window,
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


head_dialog = Dialog(
    menu_window,
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
)

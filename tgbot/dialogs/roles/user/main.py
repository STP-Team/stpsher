from aiogram_dialog import Dialog
from aiogram_dialog.widgets.kbd import Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.getters.user.user_getters import db_getter
from tgbot.dialogs.roles.user.game import game_window
from tgbot.dialogs.roles.user.kpi import (
    kpi_requirements_window,
    kpi_window,
    salary_window,
)
from tgbot.dialogs.roles.user.schedule import (
    schedule_duties_window,
    schedule_group_window,
    schedule_heads_window,
    schedule_my_window,
    schedule_window,
)
from tgbot.misc.states.user.main import UserSG

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


user_dialog = Dialog(
    menu_window,
    schedule_window,
    schedule_my_window,
    schedule_duties_window,
    schedule_group_window,
    schedule_heads_window,
    kpi_window,
    kpi_requirements_window,
    salary_window,
    game_window,
)

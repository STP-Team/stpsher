"""Кастомные кнопки для диалогов."""

from aiogram_dialog.widgets.kbd import Button, Group, Url
from aiogram_dialog.widgets.text import Const

from tgbot.dialogs.events.common.common import close_all_dialogs
from tgbot.dialogs.events.common.game.casino import change_rate
from tgbot.dialogs.events.common.game.game import start_game_dialog
from tgbot.dialogs.events.common.groups import start_groups_dialog
from tgbot.dialogs.events.common.kpi import start_kpi_dialog
from tgbot.dialogs.events.common.schedules import start_schedules_dialog
from tgbot.dialogs.events.common.search import start_search_dialog

SUPPORT_BTN = Url(Const("🛟 Помогите"), url=Const("t.me/stp_helpbot"))
HOME_BTN = Button(Const("🏠 Домой"), id="home", on_click=close_all_dialogs)
SEARCH_BTN = Button(
    Const("🕵🏻 Поиск сотрудника"), id="search", on_click=start_search_dialog
)
GROUPS_BTN = Button(Const("👯‍♀️ Группы"), id="groups", on_click=start_groups_dialog)
GAME_BTN = Button(Const("🏮 Игра"), id="game", on_click=start_game_dialog)
KPI_BTN = Button(Const("🌟 Показатели"), id="kpi", on_click=start_kpi_dialog)
SCHEDULES_BTN = Button(
    Const("📅 Графики"), id="exchanges", on_click=start_schedules_dialog
)

CASINO_RATES = Group(
    Group(
        Button(
            Const("-50"), id="rate_minus_50", on_click=change_rate, when="show_minus_50"
        ),
        Button(
            Const("-10"), id="rate_minus_10", on_click=change_rate, when="show_minus_10"
        ),
        Button(
            Const("+10"), id="rate_plus_10", on_click=change_rate, when="show_plus_10"
        ),
        Button(
            Const("+50"), id="rate_plus_50", on_click=change_rate, when="show_plus_50"
        ),
        width=4,
    ),
    Group(
        Button(
            Const("-500"),
            id="rate_minus_500",
            on_click=change_rate,
            when="show_minus_500",
        ),
        Button(
            Const("-100"),
            id="rate_minus_100",
            on_click=change_rate,
            when="show_minus_100",
        ),
        Button(
            Const("+100"),
            id="rate_plus_100",
            on_click=change_rate,
            when="show_plus_100",
        ),
        Button(
            Const("+500"),
            id="rate_plus_500",
            on_click=change_rate,
            when="show_plus_500",
        ),
        width=4,
    ),
)

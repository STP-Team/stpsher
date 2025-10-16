"""Кастомные кнопки для диалогов."""

from aiogram_dialog.widgets.kbd import Button, Group, Url
from aiogram_dialog.widgets.text import Const

from tgbot.dialogs.events.common.game.casino import change_rate

SUPPORT_BTN = Url(Const("🛟 Помогите"), url=Const("t.me/stp_helpbot"))
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

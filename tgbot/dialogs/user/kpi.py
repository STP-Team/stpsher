from aiogram_dialog.widgets.kbd import Button, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.getters.user.user_getters import kpi_getter
from tgbot.misc.states.user.main import UserSG

kpi_window = Window(
    Format("{kpi_text}"),
    Row(
        Button(
            Const("🧮 Нормативы"),
            id="calculator",
        ),
        Button(
            Const("💰 Зарплата"),
            id="salary",
        ),
    ),
    SwitchTo(Const("🔄 Обновить"), id="update", state=UserSG.kpi),
    SwitchTo(Const("↩️ Назад"), id="menu", state=UserSG.menu),
    getter=kpi_getter,
    state=UserSG.kpi,
)

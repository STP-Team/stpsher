from aiogram_dialog.widgets.kbd import (
    Row,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.misc.states.dialogs.mip import MipSG

game_window = Window(
    Format("""🏮 <b>Игра</b>"""),
    SwitchTo(
        Const("✍️ Активация предметов"),
        id="products_activation",
        state=MipSG.game_products_activation,
    ),
    Row(
        SwitchTo(
            Const("🎯 Достижения"), id="achievements", state=MipSG.game_achievements
        ),
        SwitchTo(Const("👏 Предметы"), id="products", state=MipSG.game_products),
    ),
    SwitchTo(Const("↩️ Назад"), id="menu", state=MipSG.menu),
    state=MipSG.game,
)

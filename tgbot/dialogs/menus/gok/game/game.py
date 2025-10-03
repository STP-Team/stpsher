"""Генерация окна игрового профиля для ГОК."""

from aiogram_dialog.widgets.kbd import (
    Row,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.misc.states.dialogs.gok import GokSG

game_window = Window(
    Format("""🏮 <b>Игра</b>
    
Здесь ты можешь:
- Подтверждать/отклонять покупки специалистов
- Просматривать список достижений
- Просматривать список предметов"""),
    SwitchTo(
        Const("✍️ Активация предметов"),
        id="products_activation",
        state=GokSG.game_products_activation,
    ),
    Row(
        SwitchTo(
            Const("🎯 Достижения"), id="achievements", state=GokSG.game_achievements
        ),
        SwitchTo(Const("👏 Предметы"), id="products", state=GokSG.game_products),
    ),
    SwitchTo(Const("↩️ Назад"), id="menu", state=GokSG.menu),
    state=GokSG.game,
)

from aiogram_dialog.widgets.kbd import Button, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.getters.user.user_getters import game_getter
from tgbot.misc.states.user.main import UserSG

game_window = Window(
    Format("""🏮 <b>Игра</b>

{level_info}

<blockquote expandable><b>✨ Баланс</b>
Всего заработано: {achievements_sum} баллов
Всего потрачено: {purchases_sum} баллов</blockquote>"""),
    Row(
        Button(Const("💎 Магазин"), id="shop"),
    ),
    Row(
        Button(
            Const("🎒 Инвентарь"),
            id="inventory",
        ),
        Button(
            Const("🎲 Казино"),
            id="casino",
        ),
    ),
    Row(
        Button(
            Const("🎯 Достижения"),
            id="achievements",
        )
    ),
    Row(
        Button(
            Const("📜 История баланса"),
            id="history",
        )
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="menu", state=UserSG.menu)),
    getter=game_getter,
    state=UserSG.game,
)

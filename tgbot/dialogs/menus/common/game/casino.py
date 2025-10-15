"""Генерация общих функций для игры в казино."""

from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import Button, Group, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.game.casino import (
    play_again,
    start_bowling,
    start_darts,
    start_dice,
    start_slots,
)
from tgbot.dialogs.events.common.game.game import close_game_dialog
from tgbot.dialogs.getters.common.game.casino import (
    balance_getter,
    casino_game_getter,
    casino_result_getter,
    casino_waiting_getter,
)
from tgbot.dialogs.menus.widgets import CASINO_RATES
from tgbot.dialogs.states.common.game import Game

casino_window = Window(
    Const("🎲 <b>Казино</b>\n"),
    Format("""✨ <b>Баланс:</b> {balance}

Выбери игру из списка ниже"""),
    Group(
        SwitchTo(Const("🎰 Слоты"), id="slots", state=Game.casino_slots),
        SwitchTo(Const("🎲 Кости"), id="dice", state=Game.casino_dice),
        SwitchTo(Const("🎯 Дартс"), id="darts", state=Game.casino_darts),
        SwitchTo(Const("🎳 Боулинг"), id="bowling", state=Game.casino_bowling),
        width=2,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="menu", state=Game.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_game_dialog),
    ),
    getter=balance_getter,
    state=Game.casino,
)

casino_slots_window = Window(
    Const("🎰 <b>Казино - Слоты</b>\n"),
    Format("""✨ <b>Баланс:</b> {balance} баллов

🎮 <b>Как играть</b>
1. Назначь ставку используя кнопки меню
2. Жми <b>🎰 Крутить 🎰</b>

<blockquote expandable>💎 <b>Таблица наград:</b>
🎰 Джекпот - Три семерки → x5.0
🔥 Три в ряд → x3.5
✨ Две семерки → x2.5</blockquote>"""),
    Button(Format("💰 Ставка: {current_rate}"), id="current_rate"),
    Button(Const("🎰 Крутить 🎰"), id="spin_slots", on_click=start_slots),
    CASINO_RATES,
    Row(
        SwitchTo(Const("↩️ Назад"), id="casino", state=Game.casino),
        Button(Const("🏠 Домой"), id="home", on_click=close_game_dialog),
    ),
    getter=casino_game_getter,
    state=Game.casino_slots,
)

casino_dice_window = Window(
    Const("🎲 <b>Казино - Кости</b>\n"),
    Format("""✨ <b>Баланс:</b> {balance} баллов

🎮 <b>Как играть</b>
1. Назначь ставку используя кнопки меню
2. Жми <b>🎲 Бросить кости 🎲</b>

<blockquote expandable>💎 <b>Таблица наград:</b>
🎯 Выпало 6 → x2.0
✨ Выпало 5 → x1.5
💫 Выпало 4 → x0.75</blockquote>"""),
    Button(Format("💰 Ставка: {current_rate}"), id="current_rate"),
    Button(Const("🎲 Бросить кости 🎲"), id="spin_dice", on_click=start_dice),
    CASINO_RATES,
    Row(
        SwitchTo(Const("↩️ Назад"), id="casino", state=Game.casino),
        Button(Const("🏠 Домой"), id="home", on_click=close_game_dialog),
    ),
    getter=casino_game_getter,
    state=Game.casino_dice,
)

casino_darts_window = Window(
    Const("🎯 <b>Казино - Дартс</b>\n"),
    Format("""✨ <b>Баланс:</b> {balance} баллов

🎮 <b>Как играть</b>
1. Назначь ставку используя кнопки меню
2. Жми <b>🎯 Бросить дротик 🎯</b>

<blockquote expandable>💎 <b>Таблица наград:</b>
🎯 Попадание в яблочко (6) → x2.0
✨ Близко к центру (5) → x1.5
💫 В мишень (4) → x0.75</blockquote>"""),
    Button(Format("💰 Ставка: {current_rate}"), id="current_rate"),
    Button(Const("🎯 Бросить дротик 🎯"), id="spin_darts", on_click=start_darts),
    CASINO_RATES,
    Row(
        SwitchTo(Const("↩️ Назад"), id="casino", state=Game.casino),
        Button(Const("🏠 Домой"), id="home", on_click=close_game_dialog),
    ),
    getter=casino_game_getter,
    state=Game.casino_darts,
)

casino_bowling_window = Window(
    Const("🎳 <b>Казино - Боулинг</b>\n"),
    Format("""✨ <b>Баланс:</b> {balance} баллов

🎮 <b>Как играть</b>
1. Назначь ставку используя кнопки меню
2. Жми <b>🎳 Бросить шар 🎳</b>

<blockquote expandable>💎 <b>Таблица наград:</b>
🎳 Страйк (6 кеглей) → x2.0
✨ Почти страйк (5 кеглей) → x1.5
💫 Хороший бросок (4 кегли) → x0.75</blockquote>"""),
    Button(Format("💰 Ставка: {current_rate}"), id="current_rate"),
    Button(Const("🎳 Бросить шар 🎳"), id="spin_bowling", on_click=start_bowling),
    CASINO_RATES,
    Row(
        SwitchTo(Const("↩️ Назад"), id="casino", state=Game.casino),
        Button(Const("🏠 Домой"), id="home", on_click=close_game_dialog),
    ),
    getter=casino_game_getter,
    state=Game.casino_bowling,
)

casino_waiting_window = Window(
    Format("{game_icon} <b>Крутим барабан...</b>\n"),
    Format("""💰 <b>Ставка:</b> {current_rate} баллов
⏰ <b>Ждем результат...</b>"""),
    getter=casino_waiting_getter,
    state=Game.casino_waiting,
)

casino_result_window = Window(
    Format("{result_icon} <b>{result_title}</b>\n"),
    Format("""{result_message}

💰 <b>Ставка:</b> {bet_amount} баллов
{win_message}
✨ <b>Баланс:</b> {balance}"""),
    Button(Const("🔄 Играть еще"), id="play_again_btn", on_click=play_again),
    Row(
        SwitchTo(Const("↩️ К играм"), id="casino_menu", state=Game.casino),
        Button(Const("🏠 Домой"), id="home", on_click=close_game_dialog),
    ),
    getter=casino_result_getter,
    state=Game.casino_result,
)

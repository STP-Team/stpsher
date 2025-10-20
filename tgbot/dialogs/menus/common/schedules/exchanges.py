"""Генерация окон для биржи подмен."""

from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.schedules import close_schedules_dialog
from tgbot.dialogs.states.common.schedule import Schedules

exchanges_window = Window(
    Const("🎭 <b>Биржа подмен</b>"),
    Format("""
Здесь ты можешь обменять свои рабочие часы, либо взять чужие"""),
    Row(
        SwitchTo(Const("📈 Купить"), id="exchange_buy", state=Schedules.exchange_buy),
        SwitchTo(
            Const("📉 Продать"), id="exchange_sell", state=Schedules.exchange_sell
        ),
    ),
    SwitchTo(Const("🤝 Мои подмены"), id="exchange_my", state=Schedules.exchange_my),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.menu),
        SwitchTo(Const("🏠 Домой"), id="home", state=close_schedules_dialog),
    ),
    state=Schedules.exchanges,
)

exchange_buy_window = Window(
    Const("📈 <b>Биржа: Покупка часов</b>"),
    Format("""
<tg-spoiler>Здесь пока ничего нет, но очень скоро что-то будет 🪄</tg-spoiler>"""),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.exchanges),
        SwitchTo(Const("🏠 Домой"), id="home", state=close_schedules_dialog),
    ),
    state=Schedules.exchange_buy,
)

exchange_sell_window = Window(
    Const("📉 <b>Биржа: Продажа часов</b>"),
    Format("""
<tg-spoiler>Здесь пока ничего нет, но очень скоро что-то будет 🪄</tg-spoiler>"""),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.exchanges),
        SwitchTo(Const("🏠 Домой"), id="home", state=close_schedules_dialog),
    ),
    state=Schedules.exchange_sell,
)

exchange_my_window = Window(
    Const("🤝 <b>Биржа: Мои подмены</b>"),
    Format("""
<tg-spoiler>Здесь пока ничего нет, но очень скоро что-то будет 🪄</tg-spoiler>"""),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.exchanges),
        SwitchTo(Const("🏠 Домой"), id="home", state=close_schedules_dialog),
    ),
    state=Schedules.exchange_my,
)

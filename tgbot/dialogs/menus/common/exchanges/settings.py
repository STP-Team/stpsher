import operator

from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import (
    Radio,
    Row,
    SwitchTo,
    Toggle,
)
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.schedules.schedules import close_schedules_dialog
from tgbot.dialogs.getters.common.exchanges.settings import (
    buy_filters_day_getter,
    buy_filters_shift_getter,
    buy_settings_getter,
)
from tgbot.dialogs.states.common.exchanges import Exchanges

buy_settings_window = Window(
    Const("💡 <b>Биржа: Настройки покупок</b>"),
    Format("""\n<b>Сортировка</b>
По дням: {day_filter}
По сменам: {shift_filter}

<b>Фильтры</b>
По дате: {date_sort}
По цене: {price_sort}"""),
    Row(
        SwitchTo(
            Const("🔍︎ Фильтр по дням"),
            id="exchange_buy_day_filters",
            state=Exchanges.buy_filters_day,
        ),
        SwitchTo(
            Const("🔍 Фильтр по смене"),
            id="exchange_buy_shift_filters",
            state=Exchanges.buy_filters_shift,
        ),
    ),
    Toggle(
        Format("{item[1]}"),
        id="date_sort",
        items=[
            ("nearest", "🔼 Сначала ближайшие"),
            ("far", "🔽 Сначала дальние"),
        ],
        item_id_getter=operator.itemgetter(0),
    ),
    Toggle(
        Format("{item[1]}"),
        id="price_sort",
        items=[
            ("cheap", "🔼 Сначала дешевые"),
            ("expensive", "🔽 Сначала дорогие"),
        ],
        item_id_getter=operator.itemgetter(0),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.buy),
        SwitchTo(Const("🏠 Домой"), id="home", state=close_schedules_dialog),
    ),
    getter=buy_settings_getter,
    state=Exchanges.buy_settings,
)


buy_filters_day_window = Window(
    Const("🔍 <b>Фильтр по дням</b>"),
    Format(
        "\nИспользуй этот фильтр для ограничения подмен по дню\n\n{filter_description}"
    ),
    Row(
        Radio(
            Format("🔘 {item[1]}"),
            Format("⚪️ {item[1]}"),
            id="day_filter",
            item_id_getter=lambda item: item[0],
            items="day_filter_options",
        ),
    ),
    SwitchTo(Const("🎭 К бирже"), id="to_buy_exchanges", state=Exchanges.buy),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.buy_settings),
        SwitchTo(Const("🏠 Домой"), id="home", state=close_schedules_dialog),
    ),
    getter=buy_filters_day_getter,
    state=Exchanges.buy_filters_day,
)

buy_filters_shift_window = Window(
    Const("🔍︎ <b>Фильтр по смене</b>"),
    Row(
        Radio(
            Format("🔘 {item[1]}"),
            Format("⚪️ {item[1]}"),
            id="shift_filter",
            item_id_getter=lambda item: item[0],
            items="shift_filter_options",
        ),
    ),
    SwitchTo(Const("🎭 К бирже"), id="to_buy_exchanges", state=Exchanges.buy),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.buy_settings),
        SwitchTo(Const("🏠 Домой"), id="home", state=close_schedules_dialog),
    ),
    getter=buy_filters_shift_getter,
    state=Exchanges.buy_filters_shift,
)

sell_settings_window = Window(
    Const("💡 <b>Биржа: Настройки продаж </b>"),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.sell),
        SwitchTo(Const("🏠 Домой"), id="home", state=close_schedules_dialog),
    ),
    state=Exchanges.sell_settings,
)

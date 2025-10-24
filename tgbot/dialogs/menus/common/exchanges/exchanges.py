"""Генерация окон для биржи подмен."""

from typing import Any

from aiogram import F
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import (
    Button,
    ManagedRadio,
    ManagedToggle,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.schedules.exchanges import (
    on_exchange_buy_selected,
    on_exchange_sell_selected,
)
from tgbot.dialogs.getters.common.exchanges.exchanges import (
    exchange_buy_getter,
    exchange_sell_getter,
)
from tgbot.dialogs.menus.common.exchanges.create import (
    exchange_buy_detail_window,
    exchange_sell_detail_window,
    sell_confirmation_window,
    sell_date_select_window,
    sell_hours_select_window,
    sell_payment_date_window,
    sell_payment_timing_window,
    sell_price_input_window,
    sell_time_input_window,
)
from tgbot.dialogs.menus.common.exchanges.settings import (
    buy_filters_day_window,
    buy_filters_shift_window,
    buy_settings_window,
    sell_settings_window,
)
from tgbot.dialogs.states.common.exchanges import Exchanges
from tgbot.dialogs.widgets.buttons import HOME_BTN

exchanges_window = Window(
    Const("🎭 <b>Биржа подмен</b>"),
    Format("""
Здесь ты можешь обменять свои рабочие часы, либо взять чужие"""),
    Row(
        SwitchTo(Const("📈 Купить"), id="buy", state=Exchanges.buy),
        SwitchTo(Const("📉 Продать"), id="sell", state=Exchanges.sell),
    ),
    SwitchTo(Const("🗳 Мои сделки"), id="my", state=Exchanges.my),
    SwitchTo(Const("💸 Создать сделку"), id="create", state=Exchanges.create),
    SwitchTo(Const("📊 Статистика"), id="stats", state=Exchanges.stats),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.menu), HOME_BTN),
    state=Exchanges.menu,
)

exchange_buy_window = Window(
    Const("📈 <b>Биржа: Покупка часов</b>"),
    Format(
        """\nПредложений на бирже: {exchanges_length}
        
<i>🔍 Нажми на смену для просмотра деталей</i>""",
        when="has_exchanges",
    ),
    Format("\n📭 <i>Пока биржа пуста :(</i>", when=~F["has_exchanges"]),
    ScrollingGroup(
        Select(
            Format("{item[time]}, {item[date]} | {item[price]} р."),
            id="exchange_select",
            items="available_exchanges",
            item_id_getter=lambda item: item["id"],
            on_click=on_exchange_buy_selected,
        ),
        width=1,
        height=10,
        hide_on_single_page=True,
        id="exchange_scrolling",
        when="has_exchanges",
    ),
    Button(Const("🔄 Обновить"), id="refresh_exchange_buy"),
    SwitchTo(
        Const("💡 Фильтры и сортировка"),
        id="exchanges_buy_settings",
        state=Exchanges.buy_settings,
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.menu), HOME_BTN),
    getter=exchange_buy_getter,
    state=Exchanges.buy,
)


exchange_sell_window = Window(
    Const("📉 <b>Биржа: Продажа часов</b>"),
    Format("""
Здесь ты можешь выставить свою смену на продажу, а так же посмотреть список своих текущих подмен на бирже"""),
    Format("\n📋 <b>Твои активные объявления:</b>", when="has_user_exchanges"),
    Format("🔍 <i>Нажми на объявление для управления</i>\n", when="has_user_exchanges"),
    Format(
        "\n📭 <i>У тебя пока нет активных объявлений</i>", when=~F["has_user_exchanges"]
    ),
    Select(
        Format("{item[time]}, {item[date]}"),
        id="user_exchange_select",
        items="user_exchanges",
        item_id_getter=lambda item: item["id"],
        on_click=on_exchange_sell_selected,
        when="has_user_exchanges",
    ),
    Button(Const("🔄 Обновить"), id="refresh_exchange_sell"),
    SwitchTo(
        Const("💡 Фильтры и сортировка"),
        id="exchanges_sell_settings",
        state=Exchanges.sell_settings,
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.menu), HOME_BTN),
    getter=exchange_sell_getter,
    state=Exchanges.sell,
)


exchange_my_window = Window(
    Const("🤝 <b>Биржа: Мои подмены</b>"),
    Format("""
<tg-spoiler>Здесь пока ничего нет, но очень скоро что-то будет 🪄</tg-spoiler>"""),
    Button(Const("🔄 Обновить"), id="refresh_exchange_buy"),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.menu), HOME_BTN),
    state=Exchanges.my,
)


async def on_start(_on_start: Any, dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        dialog_manager: Менеджер диалога
    """
    day_filter_checkbox: ManagedRadio = dialog_manager.find("day_filter")
    await day_filter_checkbox.set_checked("all")

    shift_filter_checkbox: ManagedRadio = dialog_manager.find("shift_filter")
    await shift_filter_checkbox.set_checked("all")

    date_sort_toggle: ManagedToggle = dialog_manager.find("date_sort")
    await date_sort_toggle.set_checked("nearest")

    price_sort_toggle: ManagedToggle = dialog_manager.find("price_sort")
    await price_sort_toggle.set_checked("cheap")


exchanges_dialog = Dialog(
    exchanges_window,
    exchange_buy_window,
    exchange_sell_window,
    exchange_my_window,
    # Окна продажи смены
    sell_date_select_window,
    sell_hours_select_window,
    sell_time_input_window,
    sell_price_input_window,
    sell_payment_timing_window,
    sell_payment_date_window,
    sell_confirmation_window,
    exchange_buy_detail_window,
    exchange_sell_detail_window,
    # Настройки покупок
    buy_settings_window,
    buy_filters_day_window,
    buy_filters_shift_window,
    # Настройки продаж
    sell_settings_window,
    on_start=on_start,
)

"""Генерация окон для биржи подмен."""

import operator
from typing import Any

from aiogram import F
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import (
    Button,
    Group,
    ManagedRadio,
    ManagedToggle,
    Row,
    Select,
    SwitchTo,
    Url,
)
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.exchanges.exchanges import (
    finish_exchanges_dialog,
    on_exchange_type_selected,
)
from tgbot.dialogs.getters.common.exchanges.exchanges import exchanges_getter
from tgbot.dialogs.menus.common.exchanges.buy import buy_detail_window, buy_window
from tgbot.dialogs.menus.common.exchanges.my import (
    edit_offer_comment_window,
    edit_offer_payment_date_window,
    edit_offer_payment_timing_window,
    edit_offer_price_window,
    my_detail_window,
    my_window,
    offer_edit_window,
)
from tgbot.dialogs.menus.common.exchanges.sell import (
    buy_confirmation_window,
    buy_time_selection_window,
    sell_confirmation_window,
    sell_detail_window,
    # New seller windows
    sell_time_selection_window,
    sell_window,
)
from tgbot.dialogs.menus.common.exchanges.settings import (
    buy_filters_day_window,
    buy_filters_shift_window,
    buy_settings_window,
    sell_settings_window,
)
from tgbot.dialogs.states.common.exchanges import Exchanges
from tgbot.dialogs.widgets.buttons import HOME_BTN

menu_window = Window(
    Const("🎭 <b>Биржа подмен</b>"),
    Format("""
Здесь ты можешь обменять свои рабочие часы, либо взять чужие"""),
    Row(
        SwitchTo(Const("📈 Купить"), id="exchanges_buy", state=Exchanges.buy),
        SwitchTo(Const("📉 Продать"), id="exchanges_sell", state=Exchanges.sell),
    ),
    SwitchTo(Const("🗳 Мои сделки"), id="exchanges_my", state=Exchanges.my),
    SwitchTo(Const("💸 Создать сделку"), id="exchanges_create", state=Exchanges.create),
    SwitchTo(Const("📊 Статистика"), id="exchanges_stats", state=Exchanges.stats),
    Group(
        Url(
            Const("📌 Регламент"),
            url=Const("clever.ertelecom.ru/content/space/4/article/12011/page/1"),
        ),
        Url(
            Const("🤝 Чат биржи"),
            url=Const("t.me/+iKZ3Ve6IwwozYjVi"),
        ),
        width=2,
        when="is_nck",
    ),
    Group(
        Url(
            Const("📌 Регламент"),
            url=Const("https://clever.ertelecom.ru/content/space/4/article/8795"),
        ),
        when=~F["is_nck"],
    ),
    Row(
        Button(Const("↩️ Назад"), id="back", on_click=finish_exchanges_dialog), HOME_BTN
    ),
    getter=exchanges_getter,
    state=Exchanges.menu,
)


create_window = Window(
    Const("💸 <b>Выбери тип сделки</b>"),
    Const("""
<blockquote><b>📈 Купить</b> - Предложение о покупке часов тобой
Твои коллеги увидят сделку в разделе <b>📉 Продать</b></blockquote>

<blockquote><b>📉 Продать</b> - Предложение о продаже твоих часов
Твои коллеги увидят сделку в разделе <b>📈 Купить</b></blockquote>"""),
    Select(
        Format("{item[1]}"),
        id="exchange_type",
        items=[
            ("buy", "📈 Купить"),
            ("sell", "📉 Продать"),
        ],
        item_id_getter=operator.itemgetter(0),
        on_click=on_exchange_type_selected,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="cancel", state=Exchanges.menu),
        HOME_BTN,
    ),
    state=Exchanges.create,
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

    exchanges_types: ManagedRadio = dialog_manager.find("exchanges_filter")
    await exchanges_types.set_checked("all")


exchanges_dialog = Dialog(
    menu_window,
    # Меню покупок
    buy_window,
    buy_detail_window,
    # Меню продаж
    sell_window,
    sell_detail_window,
    buy_time_selection_window,
    buy_confirmation_window,
    # New seller windows for responding to buy requests
    sell_time_selection_window,
    sell_confirmation_window,
    # Настройки покупок
    buy_settings_window,
    buy_filters_day_window,
    buy_filters_shift_window,
    # Настройки продаж
    sell_settings_window,
    # Меню своих сделок
    my_window,
    my_detail_window,
    # Редактирование сделки
    offer_edit_window,
    edit_offer_price_window,
    edit_offer_payment_timing_window,
    edit_offer_payment_date_window,
    edit_offer_comment_window,
    # Создание сделки
    create_window,
    on_start=on_start,
)

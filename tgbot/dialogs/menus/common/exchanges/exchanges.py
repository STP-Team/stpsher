"""Генерация окон для биржи подмен."""

import operator
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
    SwitchInlineQueryChosenChatButton,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.exchanges.exchanges import (
    finish_exchanges_dialog,
    on_exchange_apply,
    on_exchange_buy_selected,
    on_exchange_sell_selected,
    on_exchange_type_selected,
)
from tgbot.dialogs.getters.common.exchanges.create import exchange_types_getter
from tgbot.dialogs.getters.common.exchanges.exchanges import (
    exchange_buy_detail_getter,
    exchange_buy_getter,
    exchange_sell_detail_getter,
    exchange_sell_getter,
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
        SwitchTo(Const("📈 Купить"), id="buy", state=Exchanges.buy),
        SwitchTo(Const("📉 Продать"), id="sell", state=Exchanges.sell),
    ),
    SwitchTo(Const("🗳 Мои сделки"), id="my", state=Exchanges.my),
    SwitchTo(Const("💸 Создать предложение"), id="create", state=Exchanges.create),
    SwitchTo(Const("📊 Статистика"), id="stats", state=Exchanges.stats),
    Row(
        Button(Const("↩️ Назад"), id="back", on_click=finish_exchanges_dialog), HOME_BTN
    ),
    state=Exchanges.menu,
)

buy_window = Window(
    Const("📈 <b>Биржа: Покупка часов</b>"),
    Format("""
Здесь ты можешь найти и купить смены, которые продают другие сотрудники.

💰 <b>Доступно предложений:</b> {exchanges_length}"""),
    Format(
        "\n🔍 <i>Нажми на предложение для просмотра деталей</i>", when="has_exchanges"
    ),
    Format(
        "\n📭 <i>Пока никто не продает смены</i>",
        when=~F["has_exchanges"],
    ),
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


sell_window = Window(
    Const("📉 <b>Биржа: Продажа часов</b>"),
    Format("""
Здесь ты можешь найти людей, которые хотят купить смены, и продать им свои часы.

💰 <b>Запросы на покупку:</b> {buy_requests_length}"""),
    Format(
        "\n🔍 <i>Нажми на запрос для просмотра деталей</i>", when="has_buy_requests"
    ),
    Format(
        "\n📭 <i>Пока никто не ищет смены для покупки</i>",
        when=~F["has_buy_requests"],
    ),
    ScrollingGroup(
        Select(
            Format("{item[time]}, {item[date]} | {item[price]} р."),
            id="buy_request_select",
            items="available_buy_requests",
            item_id_getter=lambda item: item["id"],
            on_click=on_exchange_sell_selected,
        ),
        width=1,
        height=10,
        hide_on_single_page=True,
        id="buy_request_scrolling",
        when="has_buy_requests",
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

sell_detail = Window(
    Const("🔍 <b>Детали запроса на покупку</b>"),
    Format("""
📅 <b>Запрос:</b> {shift_date} {shift_time} ПРМ
💰 <b>Цена:</b> {price} р.

👤 <b>Покупатель:</b> {buyer_name}
💳 <b>Оплата:</b> {payment_info}"""),
    Button(Const("✅ Продать"), id="accept_buy_request", on_click=on_exchange_apply),
    SwitchInlineQueryChosenChatButton(
        Const("🔗 Поделиться"),
        query=Format("{deeplink}"),
        allow_user_chats=True,
        allow_group_chats=True,
        allow_channel_chats=False,
        allow_bot_chats=False,
        id="buy_request_deeplink",
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.sell), HOME_BTN),
    getter=exchange_sell_detail_getter,
    state=Exchanges.sell_detail,
)

buy_detail_window = Window(
    Const("🔍 <b>Детали сделки</b>"),
    Format("""
📅 <b>Предложение:</b> <code>{shift_date} {shift_time} ПРМ</code>
💰 <b>Цена:</b> <code>{price} р.</code>

👤 <b>Продавец:</b> {seller_name}
💳 <b>Оплата:</b> {payment_info}

💬 <b>Комментарий:</b>
<blockquote expandable>{comment}</blockquote>"""),
    Button(Const("✅ Купить"), id="apply", on_click=on_exchange_apply),
    SwitchInlineQueryChosenChatButton(
        Const("🔗 Поделиться"),
        query=Format("{deeplink}"),
        allow_user_chats=True,
        allow_group_chats=True,
        allow_channel_chats=False,
        allow_bot_chats=False,
        id="exchange_deeplink",
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.buy), HOME_BTN),
    getter=exchange_buy_detail_getter,
    state=Exchanges.buy_detail,
)

create_window = Window(
    Const("<b>Выбери тип предложения</b>"),
    Const("""
<blockquote><b>📈 Купить</b> - Предложение о покупке часов тобой
Твои коллеги увидят предложение в разделе <b>📉 Продать</b></blockquote>

<blockquote><b>📉 Продать</b> - Предложение о продаже твоих часов
Твои коллеги увидят предложение в разделе <b>📈 Купить</b></blockquote>"""),
    Select(
        Format("{item[1]}"),
        id="exchange_type",
        items="exchange_types",
        item_id_getter=operator.itemgetter(0),
        on_click=on_exchange_type_selected,
    ),
    Row(
        Button(Const("↩️ Назад"), id="cancel", on_click=finish_exchanges_dialog),
        HOME_BTN,
    ),
    getter=exchange_types_getter,
    state=Exchanges.create,
)

my_window = Window(
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
    menu_window,
    buy_window,
    sell_window,
    create_window,
    my_window,
    buy_detail_window,
    sell_detail,
    # Настройки покупок
    buy_settings_window,
    buy_filters_day_window,
    buy_filters_shift_window,
    # Настройки продаж
    sell_settings_window,
    on_start=on_start,
)

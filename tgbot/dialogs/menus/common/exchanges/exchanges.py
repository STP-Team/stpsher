"""Генерация окон для биржи подмен."""

from typing import Any

from aiogram import F
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import (
    Button,
    Checkbox,
    ManagedRadio,
    ManagedToggle,
    Row,
    ScrollingGroup,
    Select,
    SwitchInlineQueryChosenChatButton,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.exchanges.create import start_create_process
from tgbot.dialogs.events.common.exchanges.exchanges import (
    finish_exchanges_dialog,
    on_exchange_apply,
    on_exchange_buy_selected,
    on_exchange_cancel,
    on_exchange_sell_selected,
    on_private_change,
)
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

exchanges_window = Window(
    Const("🎭 <b>Биржа подмен</b>"),
    Format("""
Здесь ты можешь обменять свои рабочие часы, либо взять чужие"""),
    Row(
        SwitchTo(Const("📈 Купить"), id="buy", state=Exchanges.buy),
        SwitchTo(Const("📉 Продать"), id="sell", state=Exchanges.sell),
    ),
    SwitchTo(Const("🗳 Мои сделки"), id="my", state=Exchanges.my),
    Button(Const("💸 Создать предложение"), id="create", on_click=start_create_process),
    SwitchTo(Const("📊 Статистика"), id="stats", state=Exchanges.stats),
    Row(
        Button(Const("↩️ Назад"), id="back", on_click=finish_exchanges_dialog), HOME_BTN
    ),
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
    Format("\n📋 <b>Твои активные предложения:</b>", when="has_user_exchanges"),
    Format(
        "🔍 <i>Нажми на предложение для управления</i>\n", when="has_user_exchanges"
    ),
    Format(
        "\n📭 <i>У тебя пока нет активных предложений</i>",
        when=~F["has_user_exchanges"],
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

exchange_sell_detail_window = Window(
    Const("🔍 <b>Детали предложения</b>"),
    Format("""
📅 <b>Предложение:</b> {shift_date} {shift_time} ПРМ
💰 <b>Цена:</b> {price} р.
💳 <b>Оплата:</b> {payment_info}

Статус: {status_text}

📅 <b>Создано:</b> {created_at}"""),
    Button(
        Const("✋🏻 Отменить"),
        id="cancel_exchange",
        on_click=on_exchange_cancel,
        when=F["status"] == "active",  # type: ignore[arg-type]
    ),
    Row(
        Button(Const("✏️ Редактировать"), id="exchange_details_edit"),
        Button(Const("🔄 Обновить"), id="exchange_details_update"),
    ),
    Row(
        Checkbox(
            Const("🫣 Приватное"),
            Const("👀 Публичное"),
            id="private_toggle",
            on_state_changed=on_private_change,
        ),
    ),
    SwitchInlineQueryChosenChatButton(
        Const("🔗 Поделиться"),
        query=Format("{deeplink}"),
        allow_user_chats=True,
        allow_group_chats=True,
        allow_channel_chats=False,
        allow_bot_chats=False,
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.sell), HOME_BTN),
    getter=exchange_sell_detail_getter,
    state=Exchanges.sell_detail,
)

exchange_buy_detail_window = Window(
    Const("🔍 <b>Детали сделки</b>"),
    Format("""
📅 <b>Предложение:</b> {shift_date} {shift_time} ПРМ
💰 <b>Цена:</b> {price} р.

👤 <b>Продавец:</b> {seller_name}
💳 <b>Оплата:</b> {payment_info}"""),
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

"""Генерация диалога продаж на бирже."""

from aiogram import F
from aiogram_dialog import Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Row,
    ScrollingGroup,
    Select,
    SwitchInlineQueryChosenChatButton,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.exchanges.exchanges import (
    on_buy_cancel,
    on_buy_confirm,
    on_buy_full_exchange,
    on_exchange_buy,
    on_exchange_sell_selected,
    on_time_input,
)
from tgbot.dialogs.events.common.exchanges.subscriptions import (
    start_subscriptions_dialog,
)
from tgbot.dialogs.events.common.exchanges.subscriptions import (
    start_subscriptions_dialog,
)
from tgbot.dialogs.getters.common.exchanges.exchanges import (
    buy_confirmation_getter,
    buy_time_selection_getter,
    exchange_sell_detail_getter,
    exchange_sell_getter,
)
from tgbot.dialogs.states.common.exchanges import Exchanges
from tgbot.dialogs.widgets.buttons import HOME_BTN

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
    Button(
        Const("🔔 Подписки"),
        id="buy_subscriptions",
        on_click=start_subscriptions_dialog,
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.menu), HOME_BTN),
    getter=exchange_sell_getter,
    state=Exchanges.sell,
)

sell_detail_window = Window(
    Const("🔍 <b>Детали сделки</b>"),
    Format("""
{exchange_info}"""),
    Button(
        Const("✍️ Предложить сделку"), id="accept_buy_request", on_click=on_exchange_buy
    ),
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

buy_time_selection_window = Window(
    Const("⏰ <b>Выбор времени покупки</b>"),
    Format("""
📅 <b>Дата:</b> {date_str}
⏱️ <b>Доступное время:</b> {time_range} ({total_hours} ч.)
💰 <b>Оплата:</b> {price_per_hour} р./ч. (общая стоимость: {total_price} р.)

Выбери нужное время:"""),
    Button(
        Const("🔄 Полностью"),
        id="buy_full",
        on_click=on_buy_full_exchange,
    ),
    Const("\n💡 <i>Или введи конкретное время в формате ЧЧ:ММ-ЧЧ:ММ</i>"),
    Const("<i>Например: 14:00-18:00</i>"),
    TextInput(
        id="time_input",
        on_success=on_time_input,
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.sell_detail), HOME_BTN),
    getter=buy_time_selection_getter,
    state=Exchanges.buy_time_selection,
)

buy_confirmation_window = Window(
    Const("✅ <b>Подтверждение покупки</b>"),
    Format("""
📊 <b>{purchase_type}</b>

📅 <b>Дата:</b> {date_str}
⏱️ <b>Время:</b> {time_range} ({hours} ч.)
💰 <b>Цена:</b> {price_per_hour} р./ч.
💸 <b>К оплате:</b> {total_price} р.
👤 <b>Продавец:</b> {seller_name}

Подтвердить покупку?"""),
    Row(
        Button(Const("✅ Подтвердить"), id="confirm_buy", on_click=on_buy_confirm),
        Button(Const("❌ Отменить"), id="cancel_buy", on_click=on_buy_cancel),
    ),
    getter=buy_confirmation_getter,
    state=Exchanges.buy_confirmation,
)

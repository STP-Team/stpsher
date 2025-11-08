"""Генерация диалогов для покупок на бирже."""

from aiogram import F
from aiogram_dialog import Window
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
    on_exchange_buy,
    on_exchange_buy_selected,
    on_reset_filters,
)
from tgbot.dialogs.events.common.exchanges.subscriptions import (
    start_subscriptions_dialog,
)
from tgbot.dialogs.getters.common.exchanges.exchanges import (
    exchange_buy_detail_getter,
    exchange_buy_getter,
)
from tgbot.dialogs.states.common.exchanges import Exchanges
from tgbot.dialogs.widgets.buttons import HOME_BTN

buy_window = Window(
    Const("📈 <b>Биржа: Покупка часов</b>"),
    Format("""
Здесь ты можешь найти и купить часы/смены, которые продают другие сотрудники

💰 <b>Доступно сделок:</b> {exchanges_length}"""),
    Format(
        "\n<blockquote>🔍 <b>Фильтры:</b>\n{active_filters}</blockquote>",
        when="has_active_filters",
    ),
    Format(
        "\n<blockquote>🔀 <b>Сортировка:</b>\n{active_sorting}</blockquote>",
        when="has_active_sorting",
    ),
    Format("\n🔍 <i>Нажми на сделку для просмотра деталей</i>", when="has_exchanges"),
    Format(
        "\n📭 <i>Пока никто не продает смены</i>",
        when=~F["has_exchanges"],
    ),
    ScrollingGroup(
        Select(
            Format("{item[time]}, {item[date]} | {item[price]} ₽/ч."),
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
    Row(
        Button(Const("🔄 Обновить"), id="refresh_exchange_buy"),
        Button(
            Const("♻️ Сбросить"),
            id="reset_filters",
            on_click=on_reset_filters,
            when="show_reset_button",
        ),
    ),
    SwitchTo(
        Const("💡 Фильтры и сортировка"),
        id="exchanges_buy_settings",
        state=Exchanges.buy_settings,
    ),
    Button(
        Const("🔔 Подписки"),
        id="buy_subscriptions",
        on_click=start_subscriptions_dialog,
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.menu), HOME_BTN),
    getter=exchange_buy_getter,
    state=Exchanges.buy,
)


buy_detail_window = Window(
    Const("🔍 <b>Детали сделки</b>"),
    Format("""
{exchange_info}"""),
    Format(
        "\n{duty_warning}",
        when="duty_warning",
    ),
    Button(Const("✍️ Предложить сделку"), id="apply_buy", on_click=on_exchange_buy),
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

"""Окно статистики для биржи подмен."""

from aiogram import F
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Button, Cancel, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.schedules import (
    do_nothing,
    next_month,
    prev_month,
)
from tgbot.dialogs.getters.common.exchanges.stats import (
    finances_getter,
    stats_getter,
)
from tgbot.dialogs.states.common.exchanges import ExchangesStats
from tgbot.dialogs.widgets.buttons import HOME_BTN

menu_window = Window(
    Const("📊 <b>Статистика сделок</b>"),
    Format(
        """
🧮 <b>Финансы:</b>
<blockquote>📈 <b>Заработано:</b> {total_income} ₽
📉 <b>Потрачено:</b> {total_expenses} ₽

🤑 <b>Чистая прибыль</b>: {net_profit} ₽</blockquote>

💱 <b>Сделки:</b>
<blockquote><b>Всего:</b> <b>{total_exchanges}</b> ({total_exchanged_hours} часов)

<b>Покупок:</b> {total_buy} на {total_hours_bought} часов
<b>Продаж:</b> {total_sell} на {total_hours_sold} часов

💰 <b>Средние цены:</b>
<b>Покупки:</b> {avg_buy_price} ₽/час
<b>Продажи:</b> {avg_sell_price} ₽/час</blockquote>""",
        when="has_exchanges",
    ),
    # Топ покупателей
    Format(
        """
💰 <b>Топ покупателей:</b>
<blockquote>{top_buyers}</blockquote>""",
        when=F["has_exchanges"] & F["has_top_buyers"],
    ),
    # Топ продавцов
    Format(
        """
💸 <b>Топ продавцов:</b>
<blockquote>{top_sellers}</blockquote>""",
        when=F["has_exchanges"] & F["has_top_sellers"],
    ),
    Format(
        """
Пока нет сделок за выбранный период 🤷‍♂️""",
        when=~F["has_exchanges"],
    ),
    SwitchTo(Const("🗓️ По месяцам"), id="finances", state=ExchangesStats.finances),
    Row(
        Cancel(Const("↩️ Назад"), id="close_stats"),
        HOME_BTN,
    ),
    getter=stats_getter,
    state=ExchangesStats.menu,
)


month_stats_window = Window(
    Const("🗓️ <b>По месяцам</b>"),
    Format(
        """
🧮 <b>Финансы:</b>
<blockquote>📈 <b>Заработано:</b> <b>{total_income} ₽</b>
📉 <b>Потрачено:</b> <b>{total_expenses} ₽</b>

🤑 <b>Чистая прибыль:</b> {net_profit} ₽

💰 <b>Средние цены:</b>
Продажа: <b>{avg_sell_price} ₽/ч.</b>
Покупка: <b>{avg_buy_price} ₽/ч.</b></blockquote>""",
        when=F["stats_type_financial"] & F["has_exchanges"],
    ),
    # Топ продаж
    Format(
        """
💰 <b>Топ продаж:</b>
<blockquote>{top_sells_text}</blockquote>""",
        when=F["stats_type_financial"] & F["has_top_sells"],
    ),
    # Топ покупок
    Format(
        """
💸 <b>Топ покупок:</b>
<blockquote>{top_buys_text}</blockquote>""",
        when=F["stats_type_financial"] & F["has_top_buys"],
    ),
    # Топ покупателей за месяц
    Format(
        """
💰 <b>Топ покупателей:</b>
<blockquote>{top_buyers_month}</blockquote>""",
        when=F["stats_type_financial"] & F["has_top_buyers_month"],
    ),
    # Топ продавцов за месяц
    Format(
        """
💸 <b>Топ продавцов:</b>
<blockquote>{top_sellers_month}</blockquote>""",
        when=F["stats_type_financial"] & F["has_top_sellers_month"],
    ),
    Format(
        """
Пока нет сделок за выбранный период 🤷‍♂️""",
        when=~F["has_exchanges"],
    ),
    Row(
        Button(
            Const("<"),
            id="prev_month",
            on_click=prev_month,
        ),
        Button(
            Format("{month_display}"),
            id="current_month",
            on_click=do_nothing,
        ),
        Button(
            Const(">"),
            id="next_month",
            on_click=next_month,
        ),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangesStats.menu),
        HOME_BTN,
    ),
    getter=finances_getter,
    state=ExchangesStats.finances,
)


exchanges_stats_dialog = Dialog(
    menu_window,
    month_stats_window,
)

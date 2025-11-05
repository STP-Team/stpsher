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
Всего сделок совершенно: <b>{total_exchanges}</b>

📈 <b>Заработано:</b> {total_gain} ₽
📉 <b>Потрачено:</b> {total_loss} ₽

<blockquote>💸 <b>Создано:</b>
📈 <b>Покупок:</b> {owner_buy}
📉 <b>Продаж:</b> {owner_sell}</blockquote>

<blockquote>✍️ <b>Отклики:</b>
📈 <b>На покупки:</b> {counterpart_sell}
📉 <b>На продажи:</b> {counterpart_buy}</blockquote>""",
        when="has_exchanges",
    ),
    Format(
        """
Пока нет сделок за выбранный период 🤷‍♂️""",
        when=~F["has_exchanges"],
    ),
    Row(
        SwitchTo(Const("💰 Финансы"), id="finances", state=ExchangesStats.finances),
        SwitchTo(Const("🤝 Партнеры"), id="partners", state=ExchangesStats.partners),
    ),
    Row(
        Cancel(Const("↩️ Назад"), id="close_stats"),
        HOME_BTN,
    ),
    getter=stats_getter,
    state=ExchangesStats.menu,
)


finances_window = Window(
    Const("💰 <b>Финансы</b>"),
    Format(
        """
<blockquote>📈 <b>Заработано:</b> <b>{total_income} ₽</b>
📉 <b>Потрачено:</b> <b>{total_expenses} ₽</b>

📊 Чистая прибыль: <b>{net_profit} ₽</b>
⚖️ Средняя цена в час: <b>{average_amount} ₽/ч.</b></blockquote>""",
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
        Cancel(Const("↩️ Назад"), id="close_stats"),
        HOME_BTN,
    ),
    getter=finances_getter,
    state=ExchangesStats.finances,
)

partners_window = Window(
    Const("🤝 Партнеры"),
    Format(
        """
🤝 <b>Топ партнеров {period_text}:</b>
{partners_financial_text}""",
        when=F["stats_type_partners"] & F["has_partners"],
    ),
    Format(
        """
Пока нет сделок за выбранный период 🤷‍♂️""",
        when=~F["has_exchanges"],
    ),
    Row(
        Cancel(Const("↩️ Назад"), id="close_stats"),
        HOME_BTN,
    ),
    state=ExchangesStats.partners,
)


exchanges_stats_dialog = Dialog(
    menu_window,
    finances_window,
    partners_window,
)

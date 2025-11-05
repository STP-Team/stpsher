"""Окно статистики для биржи подмен."""

from aiogram import F
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Cancel, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.getters.common.exchanges.stats import stats_getter
from tgbot.dialogs.states.common.exchanges import Exchanges, ExchangesStats
from tgbot.dialogs.widgets.buttons import HOME_BTN

menu_window = Window(
    Const("📊 <b>Статистика сделок</b>"),
    Format(
        """
Всего сделок совершенно: <b>{total_exchanges}</b>

📈 <b>Заработано:</b> {total_gain} р.
📉 <b>Потрачено:</b> {total_loss} р.

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
        SwitchTo(Const("💰 Финансы"), id="finances", state=Exchanges.finances),
        SwitchTo(Const("🤝 Партнеры"), id="partners", state=Exchanges.partners),
    ),
    Row(
        Cancel(Const("↩️ Назад"), id="close_stats"),
        HOME_BTN,
    ),
    getter=stats_getter,
    state=ExchangesStats.menu,
)


finances_window = Window(
    Const("💰 Финансы"),
    Format(
        """
<blockquote>💰 <b>Финансовая статистика {period_text}:</b>
• 💵 Получено за продажи: <b>{total_income} ₽</b>
• 💸 Потрачено на покупки: <b>{total_expenses} ₽</b>
• 📊 Чистая прибыль: <b>{net_profit} ₽</b>
• 📈 Средняя сумма сделки: <b>{average_amount} ₽</b></blockquote>""",
        when=F["stats_type_financial"] & F["has_exchanges"],
    ),
    # Экстремальные сделки
    Format(
        """
🏆 <b>Рекордные сделки:</b>
<blockquote>{extreme_deals_text}</blockquote>""",
        when=F["stats_type_financial"] & F["has_extreme_deals"],
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

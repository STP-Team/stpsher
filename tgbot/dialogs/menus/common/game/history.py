"""Генерация общих функций для просмотра истории баланса."""

from aiogram_dialog.widgets.kbd import (
    Radio,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.events.common.game.history import on_transaction_click
from tgbot.dialogs.filters.user.game.history import history_filter_getter
from tgbot.dialogs.getters.common.game.history import history_detail_getter
from tgbot.dialogs.states.common.game import Game
from tgbot.dialogs.widgets.buttons import HOME_BTN

history_window = Window(
    Format("""📜 <b>История баланса</b>

Здесь отображается вся история операций с баллами

Используй фильтры для поиска нужных предметов:
🏆 - Достижение
🛒 - Предметы магазина
🎰 - Казино
✍️ - Ручная операция

<i>Всего транзакций: {total_transactions} • Показано: {filtered_count}</i>"""),
    ScrollingGroup(
        Select(
            Format("{pos}. {item[1]}"),
            id="history",
            items="history_products",
            item_id_getter=lambda item: item[0],  # Идентификатор транзакции
            on_click=on_transaction_click,
        ),
        width=2,
        height=4,
        hide_on_single_page=True,
        id="history_scroll",
    ),
    Row(
        Radio(
            Format("🔘 {item[1]}"),
            Format("⚪️ {item[1]}"),
            id="history_type_filter",
            item_id_getter=lambda item: item[0],
            items=[("all", "Все"), ("earn", "Доход"), ("spend", "Расход")],
        ),
    ),
    Row(
        Radio(
            Format("🔘 {item[1]}"),
            Format("⚪️ {item[1]}"),
            id="history_source_filter",
            item_id_getter=lambda item: item[0],
            items=[
                ("all", "📋"),
                ("achievement", "🏆"),
                ("product", "🛒"),
                ("manual", "✍️"),
                ("casino", "🎰"),
            ],
        ),
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="menu", state=Game.menu), HOME_BTN),
    getter=history_filter_getter,
    state=Game.history,
)

history_details_window = Window(
    Format("""<b>📊 Детали транзакции</b>

<b>📈 Операция</b>
{type_emoji} {type_text} <b>{amount}</b> баллов

<b>🔢 ID:</b> <code>{transaction_id}</code>

<b>📍 Источник</b>
{source_name}

<b>📅 Дата создания</b>
{created_at}"""),
    Format(
        """
<b>💬 Комментарий</b>
<blockquote expandable>{comment}</blockquote>""",
        when="comment",
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Game.history), HOME_BTN),
    getter=history_detail_getter,
    state=Game.history_details,
)

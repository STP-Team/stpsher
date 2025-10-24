"""Генерация общих функций для просмотра инвентаря."""

from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Radio,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.events.common.game.inventory import (
    on_inventory_activation_comment_input,
    on_inventory_cancel_activation,
    on_inventory_product_click,
    on_inventory_sell_product,
    on_skip_activation_comment,
    use_product,
)
from tgbot.dialogs.filters.user.game.inventory import inventory_filter_getter
from tgbot.dialogs.getters.common.game.inventory import inventory_detail_getter
from tgbot.dialogs.states.common.game import Game
from tgbot.dialogs.widgets.buttons import HOME_BTN
from tgbot.misc.helpers import get_status_emoji

inventory_window = Window(
    Format("""🎒 <b>Инвентарь</b>

Здесь ты найдешь все свои покупки, а так же их статус и многое другое

Используй фильтры для поиска нужных предметов:
📦 - Готов к использованию
⏳ - На проверке
🔒 - Не осталось использований

<i>Всего предметов приобретено: {total_bought}</i>"""),
    ScrollingGroup(
        Select(
            Format("{item[1]}"),
            id="inventory_product",
            items="products",
            item_id_getter=lambda item: item[0],
            on_click=on_inventory_product_click,
        ),
        width=2,
        height=2,
        hide_on_single_page=True,
        id="inventory_scroll",
    ),
    Radio(
        Format("🔘 {item[1]}"),
        Format("⚪️ {item[1]}"),
        id="inventory_filter",
        item_id_getter=lambda item: item[0],
        items=[
            ("all", "📋 Все"),
            ("stored", f"{get_status_emoji('stored')}"),
            ("review", f"{get_status_emoji('review')}"),
            ("used_up", f"{get_status_emoji('used_up')}"),
        ],
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="menu", state=Game.menu), HOME_BTN),
    getter=inventory_filter_getter,
    state=Game.inventory,
)


inventory_details_window = Window(
    Format("""
<b>🛍️ Предмет:</b> {product_name}

<b>📊 Статус</b>
{status_name}

<b>📍 Активаций</b>
{usage_count} из {product_count}

<b>💵 Стоимость</b>
{product_cost} баллов

<b>📝 Описание</b>
{product_description}

<blockquote expandable><b>📅 Дата покупки</b>
{bought_at}</blockquote>{comment_text}{updated_by_text}"""),
    # Кнопки действий с предметом
    Button(
        Const("🎯 Использовать"),
        id="use_product",
        on_click=use_product,
        when="can_use",
    ),
    Button(
        Const("💸 Вернуть"),
        id="sell_product",
        on_click=on_inventory_sell_product,
        when="can_sell",
    ),
    Button(
        Const("✋🏻 Отменить активацию"),
        id="cancel_activation",
        on_click=on_inventory_cancel_activation,
        when="can_cancel",
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back_to_inventory", state=Game.inventory),
        HOME_BTN,
    ),
    getter=inventory_detail_getter,
    state=Game.inventory_details,
)

inventory_activation_comment_window = Window(
    Format("""<b>💬 Комментарий к активации</b>

<b>📦 Предмет:</b> {product_name}

Ты можешь добавить комментарий к активации
Этот комментарий увидит менеджер при проверке

Напиши комментарий или нажми <b>⏩ Пропустить</b>"""),
    TextInput(
        id="activation_comment_input",
        on_success=on_inventory_activation_comment_input,
    ),
    Button(
        Const("⏩ Пропустить"),
        id="skip_comment",
        on_click=on_skip_activation_comment,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back_to_details", state=Game.inventory_details),
        HOME_BTN,
    ),
    getter=inventory_detail_getter,
    state=Game.inventory_activation_comment,
)

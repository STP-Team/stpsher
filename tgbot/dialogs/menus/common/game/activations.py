"""Генерация общих функций для просмотра списка активаций предметов."""

from aiogram_dialog.widgets.common import sync_scroll
from aiogram_dialog.widgets.kbd import (
    Button,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format, List
from aiogram_dialog.window import Window

from tgbot.dialogs.events.common.game.activations import (
    on_activation_click,
    on_approve_activation,
    on_reject_activation,
)
from tgbot.dialogs.events.common.game.game import close_game_dialog
from tgbot.dialogs.getters.common.game.activations import (
    activation_detail_getter,
    activations_getter,
)
from tgbot.dialogs.states.common.game import Game

activations_window = Window(
    Format("""✍️ <b>Активация предметов</b>

Предметов для активации: {total_activations}\n"""),
    List(
        Format("""<b>{pos}. {item[1]}</b>
<blockquote>👤 Специалист: {item[4]} из {item[5]}
📝 Описание: {item[2]}
📅 Дата покупки: {item[3]}</blockquote>\n"""),
        items="activations",
        id="activations_list",
        page_size=4,
    ),
    ScrollingGroup(
        Select(
            Format("{pos}. {item[1]}"),
            id="activation",
            items="activations",
            item_id_getter=lambda item: item[0],
            on_click=on_activation_click,
        ),
        width=2,
        height=2,
        hide_on_single_page=True,
        id="activations_scroll",
        on_page_changed=sync_scroll("activations_list"),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="menu", state=Game.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_game_dialog),
    ),
    getter=activations_getter,
    state=Game.activations,
)

activation_details_window = Window(
    Format("""<b>🎯 Активация предмета</b>

<b>🏆 О предмете</b>
<blockquote><b>Название</b>
{selected_activation[product_name]}

<b>📝 Описание</b>
{selected_activation[product_description]}

<b>💵 Стоимость</b>
{selected_activation[product_cost]} баллов

<b>📍 Активаций</b>
{selected_activation[usage_count]} ➡️ {selected_activation[next_usage_count]} ({selected_activation[product_count]} всего)</blockquote>

<b>👤 О специалисте</b>
<blockquote><b>ФИО</b>
{selected_activation[user_name]}

<b>Должность</b>
{selected_activation[user_position]} {selected_activation[user_division]}

<b>Руководитель</b>
{selected_activation[user_head]}</blockquote>

<b>📅 Дата покупки</b>
{selected_activation[bought_at]}"""),
    Row(
        Button(Const("✅ Одобрить"), id="approve", on_click=on_approve_activation),
        Button(Const("❌ Отклонить"), id="reject", on_click=on_reject_activation),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Game.activations),
        Button(Const("🏠 Домой"), id="home", on_click=close_game_dialog),
    ),
    getter=activation_detail_getter,
    state=Game.activation_details,
)

no_activations_window = Window(
    Format("""<b>✍️ Активация предметов</b>

Нет предметов, ожидающих активации 😊"""),
    SwitchTo(Const("↩️ Назад"), id="menu", state=Game.menu),
    state=Game.no_activations,
)

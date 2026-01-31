"""Генерация общих функций для просмотра списка активаций предметов."""

import operator

from aiogram_dialog.widgets.common import sync_scroll
from aiogram_dialog.widgets.input import TextInput
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
    on_activation_approve_comment_input,
    on_activation_click,
    on_activation_history_click,
    on_activation_reject_comment_input,
    on_skip_approve_comment,
    on_skip_reject_comment,
)
from tgbot.dialogs.getters.common.game.activations import (
    activation_detail_getter,
    activation_history_detail_getter,
    activations_getter,
    activations_history_getter,
)
from tgbot.dialogs.states.common.game import GameSG
from tgbot.dialogs.widgets.buttons import HOME_BTN

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
            item_id_getter=operator.itemgetter(0),
            on_click=on_activation_click,
        ),
        width=2,
        height=2,
        hide_on_single_page=True,
        id="activations_scroll",
        on_page_changed=sync_scroll("activations_list"),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="menu", state=GameSG.menu),
        SwitchTo(Const("📜 История"), id="history", state=GameSG.activations_history),
    ),
    Row(HOME_BTN),
    getter=activations_getter,
    state=GameSG.activations,
)

activation_details_window = Window(
    Format("""<b>✍️ Активация предмета</b>

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
{selected_activation[bought_at]}{user_comment_text}"""),
    Row(
        SwitchTo(
            Const("✅ Одобрить"), id="approve", state=GameSG.activation_approve_comment
        ),
        SwitchTo(
            Const("❌ Отклонить"), id="reject", state=GameSG.activation_reject_comment
        ),
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=GameSG.activations), HOME_BTN),
    getter=activation_detail_getter,
    state=GameSG.activation_details,
)

activation_approve_comment_window = Window(
    Format("""<b>💬 Комментарий при одобрении</b>

<b>📦 Предмет:</b> {selected_activation[product_name]}
<b>👤 Специалист:</b> {selected_activation[fullname]}

Ты можешь добавить комментарий к активации
Специалист получит уведомление с комментарием

Напиши комментарий или нажми <b>➡️ Пропустить</b>"""),
    TextInput(
        id="approve_comment_input",
        on_success=on_activation_approve_comment_input,
    ),
    Button(
        Const("➡️ Пропустить"),
        id="skip_approve_comment",
        on_click=on_skip_approve_comment,
    ),
    Row(
        SwitchTo(
            Const("↩️ Назад"), id="back_to_details", state=GameSG.activation_details
        ),
        HOME_BTN,
    ),
    getter=activation_detail_getter,
    state=GameSG.activation_approve_comment,
)

activation_reject_comment_window = Window(
    Format("""<b>💬 Комментарий при отклонении</b>

<b>📦 Предмет:</b> {selected_activation[product_name]}
<b>👤 Специалист:</b> {selected_activation[fullname]}

Ты можешь добавить комментарий к активации
Специалист получит уведомление с комментарием

Напиши комментарий или нажми <b>➡️ Пропустить</b>"""),
    TextInput(
        id="reject_comment_input",
        on_success=on_activation_reject_comment_input,
    ),
    Button(
        Const("➡️ Пропустить"),
        id="skip_reject_comment",
        on_click=on_skip_reject_comment,
    ),
    Row(
        SwitchTo(
            Const("↩️ Назад"), id="back_to_details", state=GameSG.activation_details
        ),
        HOME_BTN,
    ),
    getter=activation_detail_getter,
    state=GameSG.activation_reject_comment,
)

no_activations_window = Window(
    Format("""<b>✍️ Активация предметов</b>

Нет предметов, ожидающих активации 😊"""),
    Row(SwitchTo(Const("↩️ Назад"), id="menu", state=GameSG.menu), HOME_BTN),
    state=GameSG.no_activations,
)

activations_history_window = Window(
    Format("""📜 <b>История активаций</b>

Всего записей в истории: {total_history}
"""),
    List(
        Format("""<b>{pos}. {item[1]}</b>
<blockquote>👤 Специалист: {item[2]}
{item[3]}
👨‍💼 Менеджер: {item[4]}</blockquote>
"""),
        items="activations_history",
        id="history_list",
        page_size=4,
    ),
    ScrollingGroup(
        Select(
            Format("{pos}. {item[1]}"),
            id="history_activation",
            items="activations_history",
            item_id_getter=operator.itemgetter(0),
            on_click=on_activation_history_click,
        ),
        width=2,
        height=2,
        hide_on_single_page=True,
        id="history_scroll",
        on_page_changed=sync_scroll("history_list"),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back_to_activations", state=GameSG.activations),
        HOME_BTN,
    ),
    getter=activations_history_getter,
    state=GameSG.activations_history,
)

activations_history_details_window = Window(
    Format("""<b>📜 Детали активации</b>

<b>🏆 О предмете</b>
<blockquote><b>Название</b>
{history_activation[product_name]}

<b>📝 Описание</b>
{history_activation[product_description]}

<b>💵 Стоимость</b>
{history_activation[product_cost]} баллов

<b>📍 Использований</b>
{history_activation[usage_count]} из {history_activation[product_count]}</blockquote>

<b>👤 О специалисте</b>
<blockquote><b>ФИО</b>
{history_activation[user_name]}

<b>Должность</b>
{history_activation[user_position]} {history_activation[user_division]}

<b>Руководитель</b>
{history_activation[user_head]}</blockquote>

<b>👨‍💼 О менеджере</b>
<blockquote><b>ФИО</b>
{history_activation[manager_name]}

<b>Должность</b>
{history_activation[manager_position]}</blockquote>

<b>📅 Даты</b>
<blockquote><b>Покупка:</b> {history_activation[bought_at]}
<b>Обработка:</b> {history_activation[updated_at]}</blockquote>
{user_comment_text}{manager_comment_text}"""),
    Row(
        SwitchTo(
            Const("↩️ К истории"), id="back_to_history", state=GameSG.activations_history
        ),
        HOME_BTN,
    ),
    getter=activation_history_detail_getter,
    state=GameSG.activations_history_details,
)

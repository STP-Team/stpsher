"""Генерация диалога рассылок."""

from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import (
    Back,
    Button,
    Group,
    Multiselect,
    Radio,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format, Multi, Progress

from tgbot.dialogs.events.common.broadcast import (
    close_broadcast_dialog,
    on_broadcast_back_to_menu,
    on_broadcast_filter_changed,
    on_broadcast_history_item_selected,
    on_broadcast_items_confirmed,
    on_broadcast_message_during_progress,
    on_broadcast_resend,
    on_broadcast_send,
    on_broadcast_text_input,
    on_broadcast_type_selected,
)
from tgbot.dialogs.getters.common.broadcast import (
    broadcast_detail_getter,
    broadcast_history_getter,
    broadcast_info_getter,
    broadcast_progress_getter,
    broadcast_result_getter,
    broadcast_select_getter,
)
from tgbot.dialogs.states.common.broadcast import Broadcast

broadcast_window = Window(
    Const("""📢 <b>Рассылка</b>

Это меню рассылок сообщений сотрудникам

<i>Используй меню для выбора действия</i>"""),
    SwitchTo(Const("🪶 Новая рассылка"), id="new", state=Broadcast.new_broadcast),
    Row(
        SwitchTo(Const("📜 История"), id="history", state=Broadcast.history),
    ),
    Button(Const("↩️ Назад"), id="back", on_click=close_broadcast_dialog),
    state=Broadcast.menu,
)

broadcast_new_type_window = Window(
    Const("""🪶 <b>Новая рассылка</b>

Выбери получателей рассылки используя меню

<blockquote>- <b>🔰 По направлению</b> — Рассылка по выбранным направлениям
- <b>👔 По группам</b> — Рассылка сотрудникам выбранных руководителей
- <b>🌎 Всем</b> — Рассылка по всем зарегистрированным сотрудникам</blockquote>"""),
    Group(
        Select(
            Format("{item[1]}"),
            id="type",
            items=[
                ("by_division", "🔰 По направлению"),
                ("by_group", "👔 По группам"),
                ("all", "🌎 Всем"),
            ],
            item_id_getter=lambda item: item[0],
            on_click=on_broadcast_type_selected,
        ),
        width=2,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Broadcast.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_broadcast_dialog),
    ),
    state=Broadcast.new_broadcast,
)

broadcast_new_select_window = Window(
    Format("""🪶 <b>Новая рассылка</b>

{title}

<blockquote>Используй меню ниже для выбора. Можно выбрать несколько вариантов.
После выбора нажми кнопку "Продолжить"</blockquote>"""),
    Group(
        Multiselect(
            Format("✓ {item[1]}"),
            Format("{item[1]}"),
            id="items_multiselect",
            item_id_getter=lambda item: item[0],
            items="items",
        ),
        width=2,
    ),
    Radio(
        Format("🔘 {item[1]}"),
        Format("⚪️ {item[1]}"),
        id="broadcast_filters",
        items="broadcast_filters",
        item_id_getter=lambda item: item[0],
        on_click=on_broadcast_filter_changed,
    ),
    Button(Const("✅ Продолжить"), id="confirm", on_click=on_broadcast_items_confirmed),
    Row(
        Back(Const("↩️ Назад"), id="back"),
        Button(Const("🏠 Домой"), id="home", on_click=close_broadcast_dialog),
    ),
    getter=broadcast_select_getter,
    state=Broadcast.new_broadcast_select,
)

broadcast_new_text_window = Window(
    Format("""🪶 <b>Новая рассылка</b>

Тип рассылки: <b>{broadcast_type}</b>
Получатели: <i>{broadcast_targets}</i>

Введи текст для рассылки

<blockquote>- Текст поддерживает html теги
- Текст должен быть не длиннее 4096 символов</blockquote>"""),
    MessageInput(
        func=on_broadcast_text_input,
    ),
    Row(
        Back(Const("↩️ Назад"), id="back"),
        Button(Const("🏠 Домой"), id="home", on_click=close_broadcast_dialog),
    ),
    getter=broadcast_info_getter,
    state=Broadcast.new_broadcast_text,
)

broadcast_new_check_window = Window(
    Format("""🪶 <b>Новая рассылка</b>

Тип рассылки: <b>{broadcast_type}</b>
Получатели: <i>{broadcast_targets}</i>
Текст рассылки:
<blockquote expandable>{broadcast_text}</blockquote>"""),
    Button(Const("✅ Отправить"), id="send", on_click=on_broadcast_send),
    Row(
        Back(Const("↩️ Назад"), id="back"),
        Button(Const("🏠 Домой"), id="home", on_click=close_broadcast_dialog),
    ),
    getter=broadcast_info_getter,
    state=Broadcast.new_broadcast_check,
)

broadcast_new_progress_window = Window(
    Multi(
        Const("📤 <b>Отправка рассылки...</b>"),
        Format("\nОтправлено: {current} / {total}"),
        Progress("progress", 10),
        Const("\n<i>Пожалуйста, подожди, идёт отправка сообщений</i>"),
    ),
    MessageInput(on_broadcast_message_during_progress),
    getter=broadcast_progress_getter,
    state=Broadcast.new_broadcast_progress,
)

broadcast_new_result_window = Window(
    Format("""✅ <b>Рассылка завершена!</b>

Всего получателей: <b>{total_users}</b>
✅ Успешно отправлено: <b>{success_count}</b>
❌ Ошибок: <b>{error_count}</b>"""),
    Row(
        Button(
            Const("↩️ К рассылкам"),
            id="back_to_menu",
            on_click=on_broadcast_back_to_menu,
        ),
        Button(Const("🏠 Домой"), id="home", on_click=close_broadcast_dialog),
    ),
    getter=broadcast_result_getter,
    state=Broadcast.new_broadcast_result,
)

broadcast_history_window = Window(
    Format("""📜 <b>История</b>

Здесь находятся все рассылки, сделанные тобой и другими сотрудниками

<i>Нажми на рассылку для просмотра детальной информации</i>"""),
    ScrollingGroup(
        Select(
            Format(
                "{item[target]} | {item[recipients_length]} чел. | {item[created_at]}"
            ),
            id="broadcast_history",
            items="broadcasts",
            item_id_getter=lambda item: str(item["id"]),
            on_click=on_broadcast_history_item_selected,
        ),
        id="history",
        hide_on_single_page=True,
        width=1,
        height=5,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="menu", state=Broadcast.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_broadcast_dialog),
    ),
    getter=broadcast_history_getter,
    state=Broadcast.history,
)

broadcast_history_detail_window = Window(
    Format("""📜 <b>Детали рассылки</b>

<b>Создатель:</b> {creator_name}
<b>Тип:</b> {broadcast_type}
<b>Получатели:</b> {broadcast_target}
<b>Количество получателей:</b> {recipients_count} чел.
<b>Дата создания:</b> {created_at}

<b>Текст рассылки:</b>
<blockquote expandable>{broadcast_text}</blockquote>"""),
    Button(Const("🔄 Отправить снова"), id="resend", on_click=on_broadcast_resend),
    Row(
        Back(Const("↩️ Назад"), id="back"),
        Button(Const("🏠 Домой"), id="home", on_click=close_broadcast_dialog),
    ),
    getter=broadcast_detail_getter,
    state=Broadcast.history_detail,
)

broadcast_dialog = Dialog(
    broadcast_window,
    broadcast_new_type_window,
    broadcast_new_select_window,
    broadcast_new_text_window,
    broadcast_new_check_window,
    broadcast_new_progress_window,
    broadcast_new_result_window,
    broadcast_history_window,
    broadcast_history_detail_window,
)

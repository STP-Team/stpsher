"""Генерация диалога сделок пользователя."""

import operator

from aiogram import F
from aiogram_dialog import Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Checkbox,
    Group,
    Radio,
    Row,
    ScrollingGroup,
    Select,
    SwitchInlineQueryChosenChatButton,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.exchanges.exchanges import (
    on_activation_click,
    on_add_to_calendar,
    on_cancel_exchange,
    on_delete_exchange,
    on_edit_comment_input,
    on_edit_offer_comment,
    on_edit_offer_payment_timing,
    on_edit_offer_price,
    on_edit_payment_date_selected,
    on_edit_payment_timing_selected,
    on_edit_price_input,
    on_in_schedule_click,
    on_my_exchange_selected,
    on_paid_click,
    on_private_click,
    open_my_schedule,
)
from tgbot.dialogs.getters.common.exchanges.exchanges import (
    my_detail_edit_getter,
    my_detail_getter,
    my_exchanges,
)
from tgbot.dialogs.states.common.exchanges import Exchanges
from tgbot.dialogs.widgets.buttons import HOME_BTN
from tgbot.dialogs.widgets.calendars import RussianCalendar

my_window = Window(
    Const("🗳 <b>Биржа: Мои сделки</b>"),
    Format("""
Здесь отображаются вся твоя активность на бирже

💰 <b>Всего операций:</b> {length}"""),
    Format(
        "\n🔍 <i>Нажми на сделку для просмотра подробностей</i>", when="has_exchanges"
    ),
    Format(
        "\n📭 <i>У тебя пока нет операций на бирже</i>",
        when=~F["has_exchanges"],
    ),
    ScrollingGroup(
        Select(
            Format("{item[button_text]}"),
            id="my_exchange_select",
            items="my_exchanges",
            item_id_getter=lambda item: item["id"],
            on_click=on_my_exchange_selected,
        ),
        width=2,
        height=6,
        hide_on_single_page=True,
        id="my_exchange_scrolling",
        when="has_exchanges",
    ),
    Radio(
        Format("🔘 {item[1]}"),
        Format("⚪️ {item[1]}"),
        id="exchanges_filter",
        item_id_getter=operator.itemgetter(0),
        items="exchanges_types",
    ),
    Row(
        SwitchInlineQueryChosenChatButton(
            Const("🔗 В группе"),
            query=Format("group_{exchanges_deeplink}"),
            allow_user_chats=False,
            allow_group_chats=True,
            allow_channel_chats=False,
            allow_bot_chats=False,
            id="group_exchanges_deeplink",
        ),
        SwitchInlineQueryChosenChatButton(
            Const("📨 Пользователю"),
            query=Format("dm_{exchanges_deeplink}"),
            allow_user_chats=True,
            allow_group_chats=False,
            allow_channel_chats=False,
            allow_bot_chats=False,
            id="dm_exchanges_deeplink",
        ),
    ),
    Row(
        Button(Const("👔 Мой график"), id="my_schedule", on_click=open_my_schedule),
        Button(Const("🔄 Обновить"), id="refresh_my_exchanges"),
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.menu), HOME_BTN),
    getter=my_exchanges,
    state=Exchanges.my,
)

my_detail_window = Window(
    Const("🔍 <b>Детали сделки</b>"),
    Format("""
📊 <b>Статус:</b> {status_text}"""),
    Format(
        """💸 <b>Оплачено:</b> {is_paid}""",
        when="has_other_party",
    ),
    Format("""
{exchange_info}"""),
    Format("""
🔗 <b>Ссылка:</b> <code>{deeplink_url}</code>"""),
    # Кнопки активных обменов
    Group(
        SwitchInlineQueryChosenChatButton(
            Const("🔗 В группу"),
            query=Format("group_{deeplink}"),
            allow_user_chats=False,
            allow_group_chats=True,
            allow_channel_chats=False,
            allow_bot_chats=False,
            id="group_share_deeplink",
        ),
        SwitchInlineQueryChosenChatButton(
            Const("🔗 В лс"),
            query=Format("dm_{deeplink}"),
            allow_user_chats=True,
            allow_group_chats=False,
            allow_channel_chats=False,
            allow_bot_chats=False,
            id="dm_share_deeplink",
        ),
        width=2,
        when=F["status"] == "active",  # noqa
    ),
    SwitchTo(
        Const("✏️ Редактировать"),
        id="edit",
        state=Exchanges.edit_offer,
        when=F["status"] == "active",  # noqa
    ),
    # Кнопки завершенной сделки
    Group(
        Checkbox(
            Const("🟢 Оплачено"),
            Const("🟡 Не оплачено"),
            id="exchange_is_paid",
            on_click=on_paid_click,
            when=F["current_user_should_get_paid"],
        ),
        Row(
            Checkbox(
                Const("🟢 В графике"),
                Const("🟡 Не в графике"),
                id="exchange_in_schedule",
                on_click=on_in_schedule_click,
            ),
            Button(
                Const("✍🏼 В календарь"),
                id="exchange_to_calendar",
                on_click=on_add_to_calendar,
            ),
        ),
        Button(
            Const("✋ Предложить отмену"),
            id="cancel_exchange",
            on_click=on_cancel_exchange,
            when="can_cancel",
        ),
        when=F["status"] == "sold",  # noqa
    ),
    Button(Const("🔄 Обновить"), id="update"),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.my), HOME_BTN),
    getter=my_detail_getter,
    state=Exchanges.my_detail,
)

offer_edit_window = Window(
    Const("✏️ <b>Редактирование сделки</b>"),
    Format("""
Используй кнопки ниже для редактирования выбранной сделки"""),
    Row(
        Checkbox(
            Const("🟢 Активная"),
            Const("🟡 Выключена"),
            id="offer_status",
            on_click=on_activation_click,
        ),
        Checkbox(
            Const("🟡 Приватная"),
            Const("🟢 Публичная"),
            id="offer_private_status",
            on_click=on_private_click,
        ),
        when=F["status"] == "active",  # noqa
    ),
    Row(
        Button(Const("💰 Цена"), id="edit_offer_price", on_click=on_edit_offer_price),
        Button(
            Const("💳 Оплата"),
            id="edit_offer_payment_timing",
            on_click=on_edit_offer_payment_timing,
        ),
    ),
    Button(
        Const("💬 Комментарий"), id="edit_offer_comment", on_click=on_edit_offer_comment
    ),
    Button(
        Const("🔥 Удалить"),
        id="remove_my_exchange",
        on_click=on_delete_exchange,
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.my_detail), HOME_BTN),
    getter=my_detail_edit_getter,
    state=Exchanges.edit_offer,
)


edit_offer_price_window = Window(
    Const("💰 <b>Редактирование цены</b>"),
    Format("""
Введи новую цену за сделку

Цена должна быть от 1 до 50,000 рублей"""),
    TextInput(
        id="edit_price_input",
        on_success=on_edit_price_input,
    ),
    SwitchTo(Const("🔍 К сделке"), id="back_to_exchange", state=Exchanges.my_detail),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.edit_offer), HOME_BTN),
    state=Exchanges.edit_offer_price,
)

edit_offer_payment_timing_window = Window(
    Const("💳 <b>Редактирование условий оплаты</b>"),
    Const("Выбери когда должна произойти оплата:"),
    Select(
        Format("{item[1]}"),
        id="edit_payment_timing",
        items=[
            ("immediate", "🚀 Сразу"),
            ("on_date", "📅 В определенную дату"),
        ],
        item_id_getter=lambda item: item[0],
        on_click=on_edit_payment_timing_selected,
    ),
    SwitchTo(Const("🔍 К сделке"), id="back_to_exchange", state=Exchanges.my_detail),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.edit_offer), HOME_BTN),
    state=Exchanges.edit_offer_payment_timing,
)

edit_offer_payment_date_window = Window(
    Const("📅 <b>Дата оплаты</b>"),
    Const("Выбери дату когда должна произойти оплата:"),
    RussianCalendar(
        id="edit_payment_date_calendar",
        on_click=on_edit_payment_date_selected,
    ),
    SwitchTo(Const("🔍 К сделке"), id="back_to_exchange", state=Exchanges.my_detail),
    Row(
        SwitchTo(
            Const("↩️ Назад"), id="back", state=Exchanges.edit_offer_payment_timing
        ),
        HOME_BTN,
    ),
    state=Exchanges.edit_offer_payment_date,
)

edit_offer_comment_window = Window(
    Const("💬 <b>Редактирование комментария</b>"),
    Format("""
Введи новый комментарий к сделке

Максимальная длина: 500 символов
Оставь пустым для удаления комментария"""),
    TextInput(
        id="edit_comment_input",
        on_success=on_edit_comment_input,
    ),
    SwitchTo(Const("🔍 К сделке"), id="back_to_exchange", state=Exchanges.my_detail),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.edit_offer), HOME_BTN),
    state=Exchanges.edit_offer_comment,
)

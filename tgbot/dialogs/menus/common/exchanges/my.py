"""Генерация диалога сделок пользователя."""

from aiogram import F
from aiogram_dialog import Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Checkbox,
    Row,
    ScrollingGroup,
    Select,
    SwitchInlineQueryChosenChatButton,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.exchanges.exchanges import (
    on_add_to_calendar,
    on_cancel_exchange,
    on_delete_exchange,
    on_edit_comment_input,
    on_edit_date_selected,
    on_edit_date_time_input,
    on_edit_offer_comment,
    on_edit_offer_date,
    on_edit_offer_payment_timing,
    on_edit_offer_price,
    on_edit_payment_date_selected,
    on_edit_payment_timing_selected,
    on_edit_price_input,
    on_my_exchange_selected,
    on_private_change,
    on_restore_exchange,
    on_schedule_change,
)
from tgbot.dialogs.getters.common.exchanges.exchanges import (
    edit_offer_date_getter,
    my_detail_getter,
    my_exchanges,
)
from tgbot.dialogs.states.common.exchanges import Exchanges
from tgbot.dialogs.widgets.buttons import HOME_BTN
from tgbot.dialogs.widgets.calendars import RussianCalendar
from tgbot.dialogs.widgets.exchange_calendar import ExchangeCalendar

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
    Button(Const("🔄 Обновить"), id="refresh_my_exchanges"),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.menu), HOME_BTN),
    getter=my_exchanges,
    state=Exchanges.my,
)

my_detail_window = Window(
    Const("🔍 <b>Детали сделки</b>"),
    Format("""
📊 <b>Статус:</b> {status}"""),
    Format(
        """🙋‍♂️ <b>{other_party_type}:</b> {other_party_name}""",
        when="has_other_party",
    ),
    Format("""
{exchange_info}"""),
    Format(
        """
💳 <b>Оплата:</b> {payment_info}
💸 <b>Оплачено:</b> {is_paid}""",
        when="has_other_party",
    ),
    Format(
        """
📝 <b>Комментарий:</b>
<blockquote expandable>{comment}</blockquote>""",
        when="comment",
    ),
    Format("""
🔗 <b>Ссылка:</b> <code>{deeplink_url}</code>"""),
    # Кнопки для активных обменов
    SwitchInlineQueryChosenChatButton(
        Const("🔗 Поделиться"),
        query=Format("{deeplink}"),
        allow_user_chats=True,
        allow_group_chats=True,
        allow_channel_chats=False,
        allow_bot_chats=False,
        id="buy_request_deeplink",
        when=F["is_active"],
    ),
    Row(
        Button(
            Const("❤️‍🩹 Восстановить"),
            id="restore_my_exchange",
            on_click=on_restore_exchange,
            when="could_activate",
        ),
        Button(
            Const("💔 Деактивировать"),
            id="cancel_my_exchange",
            on_click=on_cancel_exchange,
            when=F["is_active"],
        ),
        Button(
            Const("🔥 Удалить"),
            id="remove_my_exchange",
            on_click=on_delete_exchange,
        ),
    ),
    # Кнопка отметки об оплате для завершенных сделок
    Button(
        Const("✅ Отметить как оплаченное"),
        id="mark_paid",
        when=F["has_other_party"] & ~F["is_paid"],
    ),
    Row(SwitchTo(Const("✏️ Редактировать"), id="edit", state=Exchanges.edit_offer)),
    Row(
        Checkbox(
            Const("🟢 В графике"),
            Const("🟡 Не в графике"),
            id="exchange_in_schedule",
            on_state_changed=on_schedule_change,
            when=F["is_active"],
        ),
        Checkbox(
            Const("🟡 Приватная"),
            Const("🟢 Публичная"),
            id="offer_private_status",
            on_state_changed=on_private_change,
            when=F["is_active"],
        ),
    ),
    Button(
        Const("✍🏼 В календарь"), id="exchange_to_calendar", on_click=on_add_to_calendar
    ),
    Row(
        SwitchTo(Const("🎭 К бирже"), id="to_exchanges", state=Exchanges.menu),
        Button(Const("🔄 Обновить"), id="update"),
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.my), HOME_BTN),
    getter=my_detail_getter,
    state=Exchanges.my_detail,
)

offer_edit_window = Window(
    Const("✏️ <b>Редактирование сделки</b>"),
    Format("""
Используй кнопки ниже для редактирования выбранной сделки"""),
    Row(
        Button(
            Const("📅 Дата и время"), id="edit_offer_date", on_click=on_edit_offer_date
        ),
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
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.my_detail), HOME_BTN),
    state=Exchanges.edit_offer,
)

edit_offer_date_window = Window(
    Const("📅 <b>Редактирование даты</b>"),
    Const("Выбери новую дату для сделки:"),
    ExchangeCalendar(
        id="edit_date_calendar",
        on_click=on_edit_date_selected,
    ),
    SwitchTo(Const("🔍 К сделке"), id="back_to_exchange", state=Exchanges.my_detail),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.edit_offer), HOME_BTN),
    getter=edit_offer_date_getter,
    state=Exchanges.edit_offer_date,
)

edit_offer_date_time_window = Window(
    Const("🕐 <b>Редактирование времени</b>"),
    Format("""
Введи новое время в формате ЧЧ:ММ-ЧЧ:ММ

Например: <code>09:00-13:00</code>
Минуты могут быть только 00 или 30
Минимальная продолжительность: 30 минут"""),
    TextInput(
        id="edit_date_time_input",
        on_success=on_edit_date_time_input,
    ),
    SwitchTo(Const("🔍 К сделке"), id="back_to_exchange", state=Exchanges.my_detail),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.edit_offer), HOME_BTN),
    state=Exchanges.edit_offer_date_time,
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

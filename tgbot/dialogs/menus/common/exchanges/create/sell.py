"""Генерация диалога создания продажи на бирже."""

import operator

from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Row,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.exchanges.create.sell import (
    on_comment_input,
    on_confirm_sell,
    on_date_selected,
    on_hours_selected,
    on_payment_date_selected,
    on_payment_timing_selected,
    on_price_input,
    on_remaining_time_selected,
    on_skip_comment,
    on_time_input,
    on_today_selected,
)
from tgbot.dialogs.events.common.exchanges.exchanges import (
    finish_exchanges_dialog,
)
from tgbot.dialogs.getters.common.exchanges.create.sell import (
    sell_comment_getter,
    sell_confirmation_getter,
    sell_date_getter,
    sell_hours_getter,
    sell_payment_date_getter,
    sell_payment_timing_getter,
    sell_price_getter,
    sell_time_input_getter,
)
from tgbot.dialogs.states.common.exchanges import ExchangeCreateSell
from tgbot.dialogs.widgets import RussianCalendar
from tgbot.dialogs.widgets.buttons import HOME_BTN
from tgbot.dialogs.widgets.exchange_calendar import ExchangeCalendar

date_window = Window(
    Const("📅 <b>Шаг 1: Выбор даты</b>"),
    Format("\nВыбери дату смены, которую хочешь продать:"),
    Format("\n<i>Значком · · помечены дни, когда у тебя есть смена</i>"),
    ExchangeCalendar(
        id="sell_date_calendar",
        on_click=on_date_selected,
    ),
    Button(Const("📍 Сегодня"), id="exchange_create_today", on_click=on_today_selected),
    Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    Row(
        Button(Const("↩️ Назад"), id="back", on_click=finish_exchanges_dialog),
        HOME_BTN,
    ),
    getter=sell_date_getter,
    state=ExchangeCreateSell.date,
)

shift_type_window = Window(
    Const("📝 <b>Шаг 2: Тип сделки</b>"),
    Format("""
<blockquote>📅 <b>Предложение:</b> <code>{selected_date}</code></blockquote>"""),
    Format("{duty_warning}", when="duty_warning"),
    Format("\nВыбери тип смены для продажи:"),
    Select(
        Format("{item[1]}"),
        id="hours_type",
        items="shift_options",
        item_id_getter=operator.itemgetter(0),
        on_click=on_hours_selected,
    ),
    Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreateSell.date),
        HOME_BTN,
    ),
    getter=sell_hours_getter,
    state=ExchangeCreateSell.shift_type,
)

hours_window = Window(
    Const("🕐 <b>Шаг 3: Время продажи</b>"),
    Format("""
<blockquote>📅 <b>Предложение:</b> <code>{selected_date}</code></blockquote>"""),
    Format("{duty_warning}", when="duty_warning"),
    Format("{sold_hours_info}", when="sold_hours_info"),
    Format("\nВведи время, которое хочешь продать:"),
    Format(
        "\n<blockquote>Формат: <code>09:00-13:00</code> или <code>14:00-18:00</code>\nЧасовой пояс: <code>Пермь (МСК+2)</code></blockquote>"
    ),
    TextInput(
        id="time_input",
        on_success=on_time_input,
    ),
    Button(
        Const("⏰ Оставшееся время"),
        id="remaining_time",
        on_click=on_remaining_time_selected,
        when="show_remaining_time_button",
    ),
    Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreateSell.date),
        HOME_BTN,
    ),
    getter=sell_time_input_getter,
    state=ExchangeCreateSell.hours,
)

price_window = Window(
    Const("💰 <b>Шаг 4: Цена продажи</b>"),
    Format(
        """
<blockquote>📅 <b>Предложение:</b> <code>{shift_time} {shift_date} ПРМ</code></blockquote>""",
    ),
    Format("\nВведи полную цену за продаваемую смену (в рублях):"),
    TextInput(
        id="price_input",
        on_success=on_price_input,
    ),
    Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    Row(
        SwitchTo(
            Const("↩️ Назад"), id="back_to_previous", state=ExchangeCreateSell.hours
        ),
        HOME_BTN,
    ),
    getter=sell_price_getter,
    state=ExchangeCreateSell.price,
)

payment_timing_window = Window(
    Const("💳 <b>Шаг 5: Условия оплаты</b>"),
    Format("""
<blockquote>📅 <b>Предложение:</b> <code>{shift_time} {shift_date} ПРМ</code>
💰 <b>Оплата:</b> <code>{price} р.</code></blockquote>"""),
    Format("\nВыбери когда поступит оплата:"),
    Select(
        Format("{item[1]}"),
        id="payment_timing",
        items=[
            ("immediate", "💸 Сразу"),
            ("on_date", "📅 Выбрать дату"),
        ],
        item_id_getter=operator.itemgetter(0),
        on_click=on_payment_timing_selected,
    ),
    Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreateSell.price),
        HOME_BTN,
    ),
    getter=sell_payment_timing_getter,
    state=ExchangeCreateSell.payment_timing,
)

payment_date_window = Window(
    Const("📅 <b>Шаг 6: Дата платежа</b>"),
    Format("""
<blockquote>📅 <b>Предложение:</b> <code>{shift_time} {shift_date} ПРМ</code>
💰 <b>Оплата:</b> <code>{price} р.</code></blockquote>"""),
    Format("\nВыбери крайнюю дату для оплаты:"),
    Format("<i>Дата должна быть не позже даты смены</i>"),
    RussianCalendar(
        id="payment_date_calendar",
        on_click=on_payment_date_selected,
    ),
    Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreateSell.payment_timing),
        HOME_BTN,
    ),
    getter=sell_payment_date_getter,
    state=ExchangeCreateSell.payment_date,
)

comment_window = Window(
    Const("💬 <b>Шаг 7: Комментарий (необязательно)</b>"),
    Format("""
<blockquote>📅 <b>Предложение:</b> <code>{shift_time} {shift_date} ПРМ</code>
💰 <b>Оплата:</b> <code>{price} р. {payment_type}</code></blockquote>"""),
    Format(
        "\nМожешь добавить комментарий к предложению продажи или нажать <b>➡️ Пропустить</b>:"
    ),
    TextInput(
        id="comment_input",
        on_success=on_comment_input,
    ),
    Row(
        Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
        Button(Const("➡️ Пропустить"), id="skip_comment", on_click=on_skip_comment),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreateSell.payment_timing),
        HOME_BTN,
    ),
    getter=sell_comment_getter,
    state=ExchangeCreateSell.comment,
)

confirmation_window = Window(
    Const("✅ <b>Шаг 8: Подтверждение сделки</b>"),
    Format("""
<blockquote>📅 <b>Предложение:</b> <code>{shift_time} {shift_date} ПРМ</code>
💰 <b>Оплата:</b> <code>{price} р. {payment_info}</code></blockquote>"""),
    Format(
        "\n💬 <b>Комментарий:</b>\n<blockquote expandable>{comment}</blockquote>",
        when="comment",
    ),
    Format("\nВсё верно? Публикуем сделку?"),
    Row(
        Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
        Button(Const("✅ Опубликовать"), id="confirm", on_click=on_confirm_sell),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreateSell.comment),
        HOME_BTN,
    ),
    getter=sell_confirmation_getter,
    state=ExchangeCreateSell.confirmation,
)

exchanges_sell_dialog = Dialog(
    date_window,
    shift_type_window,
    hours_window,
    price_window,
    payment_timing_window,
    payment_date_window,
    comment_window,
    confirmation_window,
)

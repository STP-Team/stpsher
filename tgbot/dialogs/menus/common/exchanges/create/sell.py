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
    Format("Выбери дату смены, которую хочешь продать:"),
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
    Const("⏰ <b>Тип сделки</b>"),
    Format("""
<blockquote>Дата сделки: <code>{selected_date}</code>
Твоя смена: <code>{user_schedule}</code></blockquote>"""),
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
    Const("🕐 <b>Время продажи</b>"),
    Format("Выбрана дата: <code>{selected_date}</code>"),
    Format("Твоя смена в эту дату: <code>{user_schedule}</code>"),
    Format("{duty_warning}", when="duty_warning"),
    Format("\nВведи время, которое хочешь продать"),
    Format(
        "\n<blockquote>Формат: <code>09:00-13:00</code> или <code>14:00-18:00</code></blockquote>\nЧасовой пояс: <code>Пермь (МСК+2)</code>"
    ),
    TextInput(
        id="time_input",
        on_success=on_time_input,
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
    Const("💰 <b>Цена продажи</b>"),
    Format("Дата смены: <code>{selected_date}</code>"),
    Format("Тип смены: <code>{shift_type}</code>"),
    Format("Продаваемое время: <code>{shift_time}</code>", when="shift_time"),
    Format("\nВведи полную цену за продаваемую смену (в рублях)"),
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
    Const("💳 <b>Условия оплаты</b>"),
    Format("Дата смены: <code>{selected_date}</code>"),
    Format("Тип смены: <code>{shift_type}</code>"),
    Format("Цена: <code>{price} р.</code>"),
    Format("\nВыбери когда поступит оплата"),
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
    Const("📅 <b>Дата платежа</b>"),
    Format("Дата смены: <code>{shift_date}</code>"),
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
    Const("💬 <b>Комментарий к продаже (необязательно)</b>"),
    Format("Дата смены: <code>{selected_date}</code>"),
    Format("Тип смены: <code>{shift_type}</code>"),
    Format("Цена: <code>{price} р.</code>"),
    Format(
        "\nМожешь добавить комментарий к предложению продажи или нажать <b>➡️ Пропустить</b>"
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
    Const("✅ <b>Подтверждение сделки</b>"),
    Format("""
Проверь данные перед публикацией:

📅 <b>Предложение:</b> <code>{shift_time} {shift_date} ПРМ</code>
💰 <b>Цена:</b> <code>{price} р.</code>

⏰ <b>Тип смены:</b> {shift_type}
💳 <b>Оплата:</b> {payment_info}"""),
    Format("💬 <b>Комментарий:</b> {comment}", when="comment"),
    Format("\nВсё верно?"),
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

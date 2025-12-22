"""Генерация диалога создания покупки на бирже."""

import operator

from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Cancel,
    Group,
    Row,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.exchanges.create.buy import (
    on_buy_comment_input,
    on_buy_date_selected,
    on_buy_date_skip,
    on_buy_hours_input,
    on_buy_hours_skip,
    on_buy_payment_date_selected,
    on_buy_payment_timing_selected,
    on_buy_price_input,
    on_buy_skip_comment,
    on_confirm_buy,
)
from tgbot.dialogs.events.common.exchanges.exchanges import (
    finish_exchanges_dialog,
)
from tgbot.dialogs.getters.common.exchanges.create.buy import (
    buy_comment_getter,
    buy_confirmation_getter,
    buy_date_getter,
    buy_hours_getter,
    buy_payment_date_getter,
    buy_payment_timing_getter,
    buy_price_getter,
)
from tgbot.dialogs.states.common.exchanges import ExchangeCreateBuy
from tgbot.dialogs.widgets import RussianCalendar
from tgbot.dialogs.widgets.buttons import HOME_BTN
from tgbot.dialogs.widgets.exchange_calendar import ExchangeCalendar

date_window = Window(
    Const("📅 <b>Шаг 1: Выбор даты (необязательно)</b>"),
    Format("Выбери дату, когда хочешь купить смену, или пропусти этот шаг:"),
    Format("\n<i>Значком · · помечены дни, когда у тебя есть смена</i>"),
    Format("\n<i>Если пропустишь, запрос будет действовать для любой даты</i>"),
    ExchangeCalendar(
        id="buy_date_calendar",
        on_click=on_buy_date_selected,
    ),
    Row(
        Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
        Button(Const("➡️ Пропустить"), id="skip_date", on_click=on_buy_date_skip),
    ),
    Row(
        Cancel(Const("↩️ Назад"), id="back"),
        HOME_BTN,
    ),
    getter=buy_date_getter,
    state=ExchangeCreateBuy.date,
)

hours_window = Window(
    Const("🕐 <b>Шаг 2: Время (необязательно)</b>"),
    Format("Выбранная дата: <code>{selected_date}</code>", when="selected_date"),
    Format("Любая дата", when="any_date"),
    Format("\nВведи время, которое хочешь купить, или пропусти:"),
    Format(
        "\n<blockquote>Формат: <code>09:00-13:00</code> или <code>14:00-18:00</code></blockquote>\nЧасовой пояс: <code>Пермь (МСК+2)</code>"
    ),
    Format("\n<i>Если пропустишь, запрос будет действовать для любого времени</i>"),
    TextInput(
        id="buy_hours_input",
        on_success=on_buy_hours_input,
    ),
    Row(
        Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
        Button(Const("➡️ Пропустить"), id="skip_hours", on_click=on_buy_hours_skip),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreateBuy.date),
        HOME_BTN,
    ),
    getter=buy_hours_getter,
    state=ExchangeCreateBuy.hours,
)

price_window = Window(
    Const("💰 <b>Шаг 3: Цена за час</b>"),
    Format("Выбранная дата: <code>{selected_date}</code>", when="selected_date"),
    Format("Любая дата", when="any_date"),
    Format("Время: <code>{hours_range}</code>", when="hours_range"),
    Format("Любое время", when="any_hours"),
    Format("{market_stats}"),
    Format("\nВведи цену за час работы(в рублях)"),
    Format("\n<blockquote>Например: 500</blockquote>"),
    TextInput(
        id="buy_price_input",
        on_success=on_buy_price_input,
    ),
    Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreateBuy.hours),
        HOME_BTN,
    ),
    getter=buy_price_getter,
    state=ExchangeCreateBuy.price,
)

payment_timing_window = Window(
    Const("💳 <b>Шаг 4: Условия оплаты</b>"),
    Format("""
<blockquote>📅 <b>Дата:</b> <code>{date_info}</code>
🕐 <b>Время:</b> <code>{time_info}</code>
💰 <b>Цена за час:</b> <code>{price_per_hour} ₽</code></blockquote>"""),
    Format("\nВыбери когда должна поступить оплата:"),
    Group(
        Select(
            Format("{item[1]}"),
            id="buy_payment_timing",
            items=[
                ("immediate", "💸 Сразу"),
                ("by_agreement", "🤝 По договоренности"),
                ("on_date", "📅 Выбрать дату"),
            ],
            item_id_getter=operator.itemgetter(0),
            on_click=on_buy_payment_timing_selected,
        ),
        width=1,
    ),
    Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreateBuy.price),
        HOME_BTN,
    ),
    getter=buy_payment_timing_getter,
    state=ExchangeCreateBuy.payment_timing,
)

payment_date_window = Window(
    Const("📅 <b>Шаг 5: Дата платежа</b>"),
    Format("""
<blockquote>📅 <b>Дата:</b> <code>{date_info}</code>
🕐 <b>Время:</b> <code>{time_info}</code>
💰 <b>Цена за час:</b> <code>{price_per_hour} ₽</code></blockquote>"""),
    Format("\nВыбери крайнюю дату для оплаты:"),
    Format("<i>Можно выбрать любую дату, начиная с сегодня</i>"),
    RussianCalendar(
        id="buy_payment_date_calendar",
        on_click=on_buy_payment_date_selected,
    ),
    Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreateBuy.payment_timing),
        HOME_BTN,
    ),
    getter=buy_payment_date_getter,
    state=ExchangeCreateBuy.payment_date,
)

comment_window = Window(
    Const("💬 <b>Шаг 6: Комментарий (необязательно)</b>"),
    Format("Дата: <code>{selected_date}</code>", when="selected_date"),
    Format("Дата: Любая", when="any_date"),
    Format("Время: <code>{hours_range}</code>", when="hours_range"),
    Format("Время: Любое", when="any_hours"),
    Format("Цена за час: <code>{price_per_hour} ₽</code>"),
    Format("Оплата: <code>{payment_type}</code>"),
    Format("\nМожешь добавить комментарий к запросу или нажать <b>➡️ Пропустить</b>"),
    TextInput(
        id="buy_comment_input",
        on_success=on_buy_comment_input,
    ),
    Row(
        Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
        Button(Const("➡️ Пропустить"), id="skip_comment", on_click=on_buy_skip_comment),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreateBuy.payment_timing),
        HOME_BTN,
    ),
    getter=buy_comment_getter,
    state=ExchangeCreateBuy.comment,
)

confirmation_window = Window(
    Const("✅ <b>Шаг 7: Подтверждение сделки</b>"),
    Format("""
Проверь данные перед публикацией:

📅 <b>Предложение:</b> <code>{date_info} {time_info} ПРМ</code>
💰 <b>Цена за час:</b> <code>{price_per_hour} ₽</code>
💳 <b>Оплата:</b> <code>{payment_info}</code>"""),
    Format(
        "💬 <b>Комментарий:</b>\n<blockquote expandable>{comment}</blockquote>",
        when="comment",
    ),
    Format("\nВсё верно?"),
    Row(
        Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
        Button(Const("✅ Опубликовать"), id="confirm", on_click=on_confirm_buy),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreateBuy.comment),
        HOME_BTN,
    ),
    getter=buy_confirmation_getter,
    state=ExchangeCreateBuy.confirmation,
)

exchanges_buy_dialog = Dialog(
    date_window,
    hours_window,
    price_window,
    payment_timing_window,
    payment_date_window,
    comment_window,
    confirmation_window,
)

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

from tgbot.dialogs.events.common.exchanges.create import (
    on_buy_comment_input,
    # Buy flow event handlers
    on_buy_date_selected,
    on_buy_date_skip,
    on_buy_hours_input,
    on_buy_hours_skip,
    on_buy_price_input,
    on_buy_skip_comment,
    on_comment_input,
    on_confirm_buy,
    on_confirm_sell,
    on_date_selected,
    on_exchange_type_selected,
    on_hours_selected,
    on_payment_date_selected,
    on_payment_timing_selected,
    on_price_input,
    on_skip_comment,
    on_time_input,
)
from tgbot.dialogs.events.common.exchanges.exchanges import (
    finish_exchanges_dialog,
)
from tgbot.dialogs.getters.common.exchanges.create import exchange_types_getter
from tgbot.dialogs.getters.common.exchanges.exchanges import (
    buy_comment_getter,
    buy_confirmation_getter,
    # Buy flow getters
    buy_date_getter,
    buy_hours_getter,
    buy_price_getter,
    sell_comment_getter,
    sell_confirmation_getter,
    sell_date_getter,
    sell_hours_getter,
    sell_payment_date_getter,
    sell_payment_timing_getter,
    sell_price_getter,
    sell_time_input_getter,
)
from tgbot.dialogs.states.common.exchanges import ExchangeCreate
from tgbot.dialogs.widgets import RussianCalendar
from tgbot.dialogs.widgets.buttons import HOME_BTN
from tgbot.dialogs.widgets.exchange_calendar import ExchangeCalendar

# Окна процесса продажи смены
type_window = Window(
    Const("📅 <b>Шаг 1: Выбери тип предложения</b>"),
    Const("""
<blockquote><b>📈 Купить</b> - Предложение о покупке часов тобой
Твои коллеги увидят предложение в разделе <b>📉 Продать</b></blockquote>

<blockquote><b>📉 Продать</b> - Предложение о продаже твоих часов
Твои коллеги увидят предложение в разделе <b>📈 Купить</b></blockquote>"""),
    Select(
        Format("{item[1]}"),
        id="exchange_type",
        items="exchange_types",
        item_id_getter=operator.itemgetter(0),
        on_click=on_exchange_type_selected,
    ),
    Row(
        Button(Const("↩️ Назад"), id="cancel", on_click=finish_exchanges_dialog),
        HOME_BTN,
    ),
    getter=exchange_types_getter,
    state=ExchangeCreate.type,
)


date_window = Window(
    Const("📅 <b>Шаг 2: Выбор даты смены для продажи</b>"),
    Format("Выбери дату смены, которую хочешь продать:"),
    Format("\n<i>Значком · · помечены дни, когда у тебя есть смена</i>"),
    ExchangeCalendar(
        id="sell_date_calendar",
        on_click=on_date_selected,
    ),
    Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreate.type),
        HOME_BTN,
    ),
    getter=sell_date_getter,
    state=ExchangeCreate.date,
)

shift_type_window = Window(
    Const("⏰ <b>Шаг 3: Тип смены</b>"),
    Format("Дата смены: {selected_date}"),
    Format("Твоя смена: {user_schedule}"),
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
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreate.date),
        HOME_BTN,
    ),
    getter=sell_hours_getter,
    state=ExchangeCreate.shift_type,
)

hours_window = Window(
    Const("🕐 <b>Шаг 4: Время продажи</b>"),
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
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreate.shift_type),
        HOME_BTN,
    ),
    getter=sell_time_input_getter,
    state=ExchangeCreate.hours,
)

price_window = Window(
    Const("💰 <b>Шаг 5: Цена продажи</b>"),
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
        SwitchTo(Const("↩️ Назад"), id="back_to_previous", state=ExchangeCreate.hours),
        HOME_BTN,
    ),
    getter=sell_price_getter,
    state=ExchangeCreate.price,
)

payment_timing_window = Window(
    Const("💳 <b>Шаг 6: Условия оплаты</b>"),
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
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreate.price),
        HOME_BTN,
    ),
    getter=sell_payment_timing_getter,
    state=ExchangeCreate.payment_timing,
)

payment_date_window = Window(
    Const("📅 <b>Шаг 7: Дата платежа</b>"),
    Format("Дата смены: {shift_date}"),
    Format("\nВыбери крайнюю дату для оплаты:"),
    Format("<i>Дата должна быть не позже даты смены</i>"),
    RussianCalendar(
        id="payment_date_calendar",
        on_click=on_payment_date_selected,
    ),
    Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreate.payment_timing),
        HOME_BTN,
    ),
    getter=sell_payment_date_getter,
    state=ExchangeCreate.payment_date,
)

comment_window = Window(
    Const("💬 <b>Шаг 8: Комментарий к продаже (необязательно)</b>"),
    Format("Дата смены: <code>{selected_date}</code>"),
    Format("Тип смены: <code>{shift_type}</code>"),
    Format("Цена: <code>{price} р.</code>"),
    Format(
        "\nМожешь добавить комментарий к предложению продажи или нажать 'Пропустить'"
    ),
    Format(
        "\n<blockquote>Например: 'Готов обменяться', 'Срочно продаю', 'Предпочитаю НТП' и т.д.</blockquote>"
    ),
    TextInput(
        id="comment_input",
        on_success=on_comment_input,
    ),
    Row(
        Button(Const("➡️ Пропустить"), id="skip_comment", on_click=on_skip_comment),
        Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreate.payment_timing),
        HOME_BTN,
    ),
    getter=sell_comment_getter,
    state=ExchangeCreate.comment,
)

confirmation_window = Window(
    Const("✅ <b>Подтверждение продажи</b>"),
    Format("""
Проверь данные перед публикацией предложения о продаже:

📅 <b>Дата смены:</b> {shift_date}
⏰ <b>Тип смены:</b> {shift_type}
🕘 <b>Время:</b> {shift_time}
💰 <b>Цена:</b> {price} р.
💳 <b>Оплата:</b> {payment_info}"""),
    Format("💬 <b>Комментарий:</b> {comment}", when="comment"),
    Format("\nВсё верно?"),
    Row(
        Button(
            Const("✅ Опубликовать продажу"), id="confirm", on_click=on_confirm_sell
        ),
        Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreate.comment),
        HOME_BTN,
    ),
    getter=sell_confirmation_getter,
    state=ExchangeCreate.confirmation,
)

# Buy flow windows
buy_date_window = Window(
    Const("📅 <b>Шаг 2: Выбор даты (необязательно)</b>"),
    Format("Выбери дату, когда хочешь купить смену, или пропусти этот шаг:"),
    Format("\n<i>Если пропустишь, запрос будет действовать для любой даты</i>"),
    RussianCalendar(
        id="buy_date_calendar",
        on_click=on_buy_date_selected,
    ),
    Row(
        Button(Const("➡️ Пропустить"), id="skip_date", on_click=on_buy_date_skip),
        Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreate.type),
        HOME_BTN,
    ),
    getter=buy_date_getter,
    state=ExchangeCreate.buy_date,
)

buy_hours_window = Window(
    Const("🕐 <b>Шаг 3: Время (необязательно)</b>"),
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
        Button(Const("➡️ Пропустить"), id="skip_hours", on_click=on_buy_hours_skip),
        Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreate.buy_date),
        HOME_BTN,
    ),
    getter=buy_hours_getter,
    state=ExchangeCreate.buy_hours,
)

buy_price_window = Window(
    Const("💰 <b>Шаг 4: Цена за час</b>"),
    Format("Выбранная дата: <code>{selected_date}</code>", when="selected_date"),
    Format("Любая дата", when="any_date"),
    Format("Время: <code>{hours_range}</code>", when="hours_range"),
    Format("Любое время", when="any_hours"),
    Format("\nВведи цену за час, которую готов платить (в рублях)"),
    Format("\n<blockquote>Например: 500 (за один час работы)</blockquote>"),
    TextInput(
        id="buy_price_input",
        on_success=on_buy_price_input,
    ),
    Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreate.buy_hours),
        HOME_BTN,
    ),
    getter=buy_price_getter,
    state=ExchangeCreate.buy_price,
)

buy_comment_window = Window(
    Const("💬 <b>Шаг 5: Комментарий (необязательно)</b>"),
    Format("Дата: <code>{selected_date}</code>", when="selected_date"),
    Format("Дата: Любая", when="any_date"),
    Format("Время: <code>{hours_range}</code>", when="hours_range"),
    Format("Время: Любое", when="any_hours"),
    Format("Цена за час: <code>{price_per_hour} р.</code>"),
    Format("\nМожешь добавить комментарий к запросу или нажать 'Пропустить'"),
    Format(
        "\n<blockquote>Например: 'Срочно нужна смена', 'Предпочитаю НТП', 'Готов доплатить' и т.д.</blockquote>"
    ),
    TextInput(
        id="buy_comment_input",
        on_success=on_buy_comment_input,
    ),
    Row(
        Button(Const("➡️ Пропустить"), id="skip_comment", on_click=on_buy_skip_comment),
        Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreate.buy_price),
        HOME_BTN,
    ),
    getter=buy_comment_getter,
    state=ExchangeCreate.buy_comment,
)

buy_confirmation_window = Window(
    Const("✅ <b>Подтверждение запроса</b>"),
    Format("""
Проверь данные перед публикацией:

📅 <b>Дата:</b> {date_info}
🕐 <b>Время:</b> {time_info}
💰 <b>Цена за час:</b> {price_per_hour} р."""),
    Format("💬 <b>Комментарий:</b> {comment}", when="comment"),
    Format("\nВсё верно?"),
    Row(
        Button(Const("✅ Опубликовать"), id="confirm", on_click=on_confirm_buy),
        Button(Const("✋ Отмена"), id="cancel", on_click=finish_exchanges_dialog),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangeCreate.buy_comment),
        HOME_BTN,
    ),
    getter=buy_confirmation_getter,
    state=ExchangeCreate.buy_confirmation,
)


exchange_create_dialog = Dialog(
    # Shared window
    type_window,
    # Sell flow windows
    date_window,
    shift_type_window,
    hours_window,
    price_window,
    payment_timing_window,
    payment_date_window,
    comment_window,
    confirmation_window,
    # Buy flow windows
    buy_date_window,
    buy_hours_window,
    buy_price_window,
    buy_comment_window,
    buy_confirmation_window,
)

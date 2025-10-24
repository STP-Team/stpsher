import operator

from aiogram import F
from aiogram_dialog import Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Row,
    Select,
    SwitchInlineQueryChosenChatButton,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.schedules.exchanges import (
    on_cancel_sell,
    on_confirm_sell,
    on_date_selected,
    on_exchange_apply,
    on_exchange_cancel,
    on_hours_selected,
    on_payment_date_selected,
    on_payment_timing_selected,
    on_price_input,
    on_time_input,
)
from tgbot.dialogs.getters.common.exchanges.exchanges import (
    exchange_buy_detail_getter,
    exchange_sell_detail_getter,
    sell_confirmation_getter,
    sell_date_getter,
    sell_hours_getter,
    sell_payment_date_getter,
    sell_payment_timing_getter,
    sell_price_getter,
    sell_time_input_getter,
)
from tgbot.dialogs.states.common.exchanges import Exchanges
from tgbot.dialogs.widgets import RussianCalendar
from tgbot.dialogs.widgets.buttons import HOME_BTN
from tgbot.dialogs.widgets.exchange_calendar import ExchangeCalendar

# Окна процесса продажи смены

sell_date_select_window = Window(
    Const("📅 <b>Шаг 1: Выбор даты смены</b>"),
    Format("Выбери дату смены, которую хочешь продать:"),
    Format("<i>👨🏻‍💻👩🏻‍💻 — дни когда у тебя есть смена</i>"),
    ExchangeCalendar(
        id="sell_date_calendar",
        on_click=on_date_selected,
    ),
    Row(Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel_sell), HOME_BTN),
    getter=sell_date_getter,
    state=Exchanges.sell_date_select,
)

sell_hours_select_window = Window(
    Const("⏰ <b>Шаг 2: Тип смены</b>"),
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
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.sell_date_select),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel_sell),
    ),
    getter=sell_hours_getter,
    state=Exchanges.sell_hours_select,
)

sell_time_input_window = Window(
    Const("🕐 <b>Шаг 3: Время продажи</b>"),
    Format("Дата смены: {selected_date}"),
    Format("Твоя смена: {user_schedule}"),
    Format("{duty_warning}", when="duty_warning"),
    Format("\nВведи время которое хочешь продать:"),
    Format("<i>Формат: 09:00-13:00 или 14:00-18:00. Часовой пояс: Пермь (МСК+2)</i>"),
    TextInput(
        id="time_input",
        on_success=on_time_input,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.sell_hours_select),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel_sell),
    ),
    getter=sell_time_input_getter,
    state=Exchanges.sell_time_input,
)

sell_price_input_window = Window(
    Const("💰 <b>Шаг 4: Цена</b>"),
    Format("Дата смены: {selected_date}"),
    Format("Тип смены: {shift_type}"),
    Format("Время: {shift_time}", when="shift_time"),
    Format("\nВведи цену за {shift_type} (в рублях):"),
    Format("<i>Например: 1000</i>"),
    TextInput(
        id="price_input",
        on_success=on_price_input,
    ),
    Row(
        SwitchTo(
            Const("↩️ Назад"), id="back_to_previous", state=Exchanges.sell_hours_select
        ),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel_sell),
    ),
    getter=sell_price_getter,
    state=Exchanges.sell_price_input,
)

sell_payment_timing_window = Window(
    Const("💳 <b>Шаг 5: Условия оплаты</b>"),
    Format("Дата смены: {selected_date}"),
    Format("Тип смены: {shift_type}"),
    Format("Цена: {price} р."),
    Format("\nКогда поступит оплата:"),
    Select(
        Format("{item[1]}"),
        id="payment_timing",
        items=[
            ("immediate", "💸 Сразу при покупке"),
            ("on_date", "📅 До определенной даты"),
        ],
        item_id_getter=operator.itemgetter(0),
        on_click=on_payment_timing_selected,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.sell_price_input),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel_sell),
    ),
    getter=sell_payment_timing_getter,
    state=Exchanges.sell_payment_timing,
)

sell_payment_date_window = Window(
    Const("📅 <b>Шаг 6: Дата платежа</b>"),
    Format("Дата смены: {shift_date}"),
    Format("\nВыбери крайнюю дату для оплаты:"),
    Format("<i>Дата должна быть не позже даты смены</i>"),
    RussianCalendar(
        id="payment_date_calendar",
        on_click=on_payment_date_selected,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.sell_payment_timing),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel_sell),
    ),
    getter=sell_payment_date_getter,
    state=Exchanges.sell_payment_date,
)

sell_confirmation_window = Window(
    Const("✅ <b>Подтверждение</b>"),
    Format("""
Проверь данные перед публикацией:

📅 <b>Дата смены:</b> {shift_date}
⏰ <b>Тип смены:</b> {shift_type}
🕘 <b>Время:</b> {shift_time}
💰 <b>Цена:</b> {price} р.
💳 <b>Оплата:</b> {payment_info}

Всё верно?"""),
    Row(
        Button(Const("✅ Опубликовать"), id="confirm", on_click=on_confirm_sell),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel_sell),
    ),
    SwitchTo(Const("↩️ Изменить"), id="back", state=Exchanges.sell_payment_timing),
    getter=sell_confirmation_getter,
    state=Exchanges.sell_confirmation,
)

# Окна детального просмотра обменов

exchange_buy_detail_window = Window(
    Const("🔍 <b>Детали сделки</b>"),
    Format("""
📅 <b>Предложение:</b> {shift_date} {shift_time} ПРМ
💰 <b>Цена:</b> {price} р.

👤 <b>Продавец:</b> {seller_name}
💳 <b>Оплата:</b> {payment_info}"""),
    Button(Const("✅ Купить"), id="apply", on_click=on_exchange_apply),
    SwitchInlineQueryChosenChatButton(
        Const("🔗 Поделиться"),
        query=Format("{deeplink}"),
        allow_user_chats=True,
        allow_group_chats=True,
        allow_channel_chats=False,
        allow_bot_chats=False,
        id="exchange_deeplink",
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.buy), HOME_BTN),
    getter=exchange_buy_detail_getter,
    state=Exchanges.buy_detail,
)

exchange_sell_detail_window = Window(
    Const("🔍 <b>Детали объявления</b>"),
    Format("""
📅 <b>Предложение:</b> {shift_date} {shift_time} ПРМ
💰 <b>Цена:</b> {price} р.
💳 <b>Оплата:</b> {payment_info}

Статус: {status_text}

📅 <b>Создано:</b> {created_at}"""),
    Button(
        Const("✋🏻 Отменить"),
        id="cancel_exchange",
        on_click=on_exchange_cancel,
        when=F["status"] == "active",  # type: ignore[arg-type]
    ),
    Row(
        Button(Const("✏️ Редактировать"), id="exchange_details_edit"),
        Button(Const("🔄 Обновить"), id="exchange_details_update"),
    ),
    SwitchInlineQueryChosenChatButton(
        Const("🔗 Поделиться"),
        query=Format("{deeplink}"),
        allow_user_chats=True,
        allow_group_chats=True,
        allow_channel_chats=False,
        allow_bot_chats=False,
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.sell), HOME_BTN),
    getter=exchange_sell_detail_getter,
    state=Exchanges.sell_detail,
)

"""Генерация окон для биржи подмен."""

from aiogram import F
from aiogram_dialog import Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Row, Select, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.exchanges import (
    on_cancel_sell,
    on_confirm_sell,
    on_date_selected,
    on_exchange_apply,
    on_exchange_buy_selected,
    on_exchange_cancel,
    on_exchange_sell_selected,
    on_hours_selected,
    on_payment_date_selected,
    on_payment_timing_selected,
    on_price_input,
    on_time_input,
    start_sell_process,
)
from tgbot.dialogs.events.common.schedules import close_schedules_dialog
from tgbot.dialogs.getters.common.exchanges import (
    exchange_buy_detail_getter,
    exchange_buy_getter,
    exchange_sell_detail_getter,
    exchange_sell_getter,
    sell_confirmation_getter,
    sell_date_getter,
    sell_hours_getter,
    sell_payment_date_getter,
    sell_payment_timing_getter,
    sell_price_getter,
    sell_time_input_getter,
)
from tgbot.dialogs.states.common.schedule import Schedules
from tgbot.dialogs.widgets import RussianCalendar
from tgbot.dialogs.widgets.exchange_calendar import ExchangeCalendar

exchanges_window = Window(
    Const("🎭 <b>Биржа подмен</b>"),
    Format("""
Здесь ты можешь обменять свои рабочие часы, либо взять чужие"""),
    Row(
        SwitchTo(Const("📈 Купить"), id="exchange_buy", state=Schedules.exchange_buy),
        SwitchTo(
            Const("📉 Продать"), id="exchange_sell", state=Schedules.exchange_sell
        ),
    ),
    SwitchTo(Const("🤝 Мои подмены"), id="exchange_my", state=Schedules.exchange_my),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.menu),
        SwitchTo(Const("🏠 Домой"), id="home", state=close_schedules_dialog),
    ),
    state=Schedules.exchanges,
)

exchange_buy_window = Window(
    Const("📈 <b>Биржа: Покупка часов</b>"),
    Format("\n🔍 <i>Нажми на смену для просмотра деталей</i>\n", when="has_exchanges"),
    Format("\n📭 <i>Пока биржа пуста :(</i>", when=~F["has_exchanges"]),
    Select(
        Format("{item[time]}, {item[date]}"),
        id="exchange_select",
        items="available_exchanges",
        item_id_getter=lambda item: item["id"],
        on_click=on_exchange_buy_selected,
        when="has_exchanges",
    ),
    Button(Const("🔄 Обновить"), id="refresh_exchange_buy"),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.exchanges),
        SwitchTo(Const("🏠 Домой"), id="home", state=close_schedules_dialog),
    ),
    getter=exchange_buy_getter,
    state=Schedules.exchange_buy,
)

exchange_sell_window = Window(
    Const("📉 <b>Биржа: Продажа часов</b>"),
    Format("""
Здесь ты можешь выставить свою смену на продажу, а так же посмотреть список своих текущих подмен на бирже"""),
    Button(Const("💰 Продать смену"), id="start_sell", on_click=start_sell_process),
    Format("\n📋 <b>Твои активные объявления:</b>", when="has_user_exchanges"),
    Format("🔍 <i>Нажми на объявление для управления</i>\n", when="has_user_exchanges"),
    Format(
        "\n📭 <i>У тебя пока нет активных объявлений</i>", when=~F["has_user_exchanges"]
    ),
    Select(
        Format("{item[time]}, {item[date]}"),
        id="user_exchange_select",
        items="user_exchanges",
        item_id_getter=lambda item: item["id"],
        on_click=on_exchange_sell_selected,
        when="has_user_exchanges",
    ),
    Button(Const("🔄 Обновить"), id="refresh_exchange_sell"),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.exchanges),
        SwitchTo(Const("🏠 Домой"), id="home", state=close_schedules_dialog),
    ),
    getter=exchange_sell_getter,
    state=Schedules.exchange_sell,
)

exchange_my_window = Window(
    Const("🤝 <b>Биржа: Мои подмены</b>"),
    Format("""
<tg-spoiler>Здесь пока ничего нет, но очень скоро что-то будет 🪄</tg-spoiler>"""),
    Button(Const("🔄 Обновить"), id="refresh_exchange_buy"),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.exchanges),
        SwitchTo(Const("🏠 Домой"), id="home", state=close_schedules_dialog),
    ),
    state=Schedules.exchange_my,
)

# Окна процесса продажи смены

sell_date_select_window = Window(
    Const("📅 <b>Шаг 1: Выбор даты смены</b>"),
    Format("Выбери дату смены, которую хочешь продать:"),
    Format("<i>👨🏻‍💻👩🏻‍💻 — дни когда у тебя есть смена</i>"),
    ExchangeCalendar(
        id="sell_date_calendar",
        on_click=on_date_selected,
    ),
    Row(
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel_sell),
        SwitchTo(Const("🏠 Домой"), id="home", state=close_schedules_dialog),
    ),
    getter=sell_date_getter,
    state=Schedules.sell_date_select,
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
        item_id_getter=lambda item: item[0],
        on_click=on_hours_selected,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.sell_date_select),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel_sell),
    ),
    getter=sell_hours_getter,
    state=Schedules.sell_hours_select,
)

sell_time_input_window = Window(
    Const("🕐 <b>Шаг 3: Время продажи</b>"),
    Format("Дата смены: {selected_date}"),
    Format("Твоя смена: {user_schedule}"),
    Format("{duty_warning}", when="duty_warning"),
    Format("\nВведи время которое хочешь продать:"),
    Format("<i>Формат: 09:00-13:00 или 14:00-18:00</i>"),
    TextInput(
        id="time_input",
        on_success=on_time_input,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.sell_hours_select),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel_sell),
    ),
    getter=sell_time_input_getter,
    state=Schedules.sell_time_input,
)

sell_price_input_window = Window(
    Const("💰 <b>Шаг 4: Цена</b>"),
    Format("Дата смены: {selected_date}"),
    Format("Тип смены: {shift_type}"),
    Format("Время: {shift_time}", when="shift_time"),
    Format("\nВведи цену за {shift_type} (в рублях):"),
    Format("<i>Например: 1000 или 1500.50</i>"),
    TextInput(
        id="price_input",
        on_success=on_price_input,
    ),
    Row(
        SwitchTo(
            Const("↩️ Назад"), id="back_to_previous", state=Schedules.sell_hours_select
        ),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel_sell),
    ),
    getter=sell_price_getter,
    state=Schedules.sell_price_input,
)

sell_payment_timing_window = Window(
    Const("💳 <b>Шаг 5: Условия оплаты</b>"),
    Format("Дата смены: {selected_date}"),
    Format("Тип смены: {shift_type}"),
    Format("Цена: {price} руб."),
    Format("\nКогда поступит оплата:"),
    Select(
        Format("{item[1]}"),
        id="payment_timing",
        items=[
            ("immediate", "💸 Сразу при покупке"),
            ("on_date", "📅 До определенной даты"),
        ],
        item_id_getter=lambda item: item[0],
        on_click=on_payment_timing_selected,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.sell_price_input),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel_sell),
    ),
    getter=sell_payment_timing_getter,
    state=Schedules.sell_payment_timing,
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
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.sell_payment_timing),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel_sell),
    ),
    getter=sell_payment_date_getter,
    state=Schedules.sell_payment_date,
)

sell_confirmation_window = Window(
    Const("✅ <b>Подтверждение</b>"),
    Format("""
Проверь данные перед публикацией:

📅 <b>Дата смены:</b> {shift_date}
⏰ <b>Тип смены:</b> {shift_type}
🕘 <b>Время:</b> {shift_time}
💰 <b>Цена:</b> {price} руб.
💳 <b>Оплата:</b> {payment_info}

Всё верно?"""),
    Row(
        Button(Const("✅ Опубликовать"), id="confirm", on_click=on_confirm_sell),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel_sell),
    ),
    SwitchTo(Const("↩️ Изменить"), id="back", state=Schedules.sell_payment_timing),
    getter=sell_confirmation_getter,
    state=Schedules.sell_confirmation,
)

# Окна детального просмотра обменов

exchange_buy_detail_window = Window(
    Const("🔍 <b>Детали смены для покупки</b>"),
    Format("""
📅 <b>Предложение:</b> {shift_date} {shift_time}
💰 <b>Цена:</b> {price} руб.

👤 <b>Продавец:</b> {seller_name}
💳 <b>Оплата:</b> {payment_info}"""),
    Button(Const("✅ Купить"), id="apply", on_click=on_exchange_apply),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.exchange_buy),
        Button(Const("🏠 Домой"), id="home", on_click=close_schedules_dialog),
    ),
    getter=exchange_buy_detail_getter,
    state=Schedules.exchange_buy_detail,
)

exchange_sell_detail_window = Window(
    Const("🔍 <b>Детали твоего объявления</b>"),
    Format("""
📅 <b>Предложение:</b> {shift_date} {shift_time}
💰 <b>Оплата:</b> {price} руб. {payment_info}

📅 <b>Создано:</b> {created_at}"""),
    Row(
        Button(
            Const("✋🏻 Отменить"),
            id="cancel_exchange",
            on_click=on_exchange_cancel,
        ),
        Button(Const("🔄 Обновить"), id="refresh_exchange_detail"),
    ),
    SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.exchange_sell),
    getter=exchange_sell_detail_getter,
    state=Schedules.exchange_sell_detail,
)

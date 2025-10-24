"""Генерация окон для биржи подмен."""

from typing import Any

from aiogram import F
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    Button,
    ManagedRadio,
    ManagedToggle,
    Row,
    ScrollingGroup,
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
    on_exchange_buy_selected,
    on_exchange_cancel,
    on_exchange_sell_selected,
    on_hours_selected,
    on_payment_date_selected,
    on_payment_timing_selected,
    on_price_input,
    on_time_input,
)
from tgbot.dialogs.getters.common.exchanges.exchanges import (
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
from tgbot.dialogs.menus.common.exchanges.settings import (
    buy_filters_day_window,
    buy_filters_shift_window,
    buy_settings_window,
    sell_settings_window,
)
from tgbot.dialogs.states.common.exchanges import Exchanges
from tgbot.dialogs.widgets import RussianCalendar
from tgbot.dialogs.widgets.buttons import HOME_BTN
from tgbot.dialogs.widgets.exchange_calendar import ExchangeCalendar

exchanges_window = Window(
    Const("🎭 <b>Биржа подмен</b>"),
    Format("""
Здесь ты можешь обменять свои рабочие часы, либо взять чужие"""),
    Row(
        SwitchTo(Const("📈 Купить"), id="buy", state=Exchanges.buy),
        SwitchTo(Const("📉 Продать"), id="sell", state=Exchanges.sell),
    ),
    SwitchTo(Const("🗳 Мои сделки"), id="my", state=Exchanges.my),
    SwitchTo(Const("💸 Создать сделку"), id="create", state=Exchanges.create),
    SwitchTo(Const("📊 Статистика"), id="stats", state=Exchanges.stats),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.menu), HOME_BTN),
    state=Exchanges.menu,
)

exchange_buy_window = Window(
    Const("📈 <b>Биржа: Покупка часов</b>"),
    Format(
        """\nПредложений на бирже: {exchanges_length}
        
<i>🔍 Нажми на смену для просмотра деталей</i>""",
        when="has_exchanges",
    ),
    Format("\n📭 <i>Пока биржа пуста :(</i>", when=~F["has_exchanges"]),
    ScrollingGroup(
        Select(
            Format("{item[time]}, {item[date]} | {item[price]} р."),
            id="exchange_select",
            items="available_exchanges",
            item_id_getter=lambda item: item["id"],
            on_click=on_exchange_buy_selected,
        ),
        width=1,
        height=10,
        hide_on_single_page=True,
        id="exchange_scrolling",
        when="has_exchanges",
    ),
    Button(Const("🔄 Обновить"), id="refresh_exchange_buy"),
    SwitchTo(
        Const("💡 Фильтры и сортировка"),
        id="exchanges_buy_settings",
        state=Exchanges.buy_settings,
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.menu), HOME_BTN),
    getter=exchange_buy_getter,
    state=Exchanges.buy,
)


exchange_sell_window = Window(
    Const("📉 <b>Биржа: Продажа часов</b>"),
    Format("""
Здесь ты можешь выставить свою смену на продажу, а так же посмотреть список своих текущих подмен на бирже"""),
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
    SwitchTo(
        Const("💡 Фильтры и сортировка"),
        id="exchanges_sell_settings",
        state=Exchanges.sell_settings,
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.menu), HOME_BTN),
    getter=exchange_sell_getter,
    state=Exchanges.sell,
)


exchange_my_window = Window(
    Const("🤝 <b>Биржа: Мои подмены</b>"),
    Format("""
<tg-spoiler>Здесь пока ничего нет, но очень скоро что-то будет 🪄</tg-spoiler>"""),
    Button(Const("🔄 Обновить"), id="refresh_exchange_buy"),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.menu), HOME_BTN),
    state=Exchanges.my,
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
        item_id_getter=lambda item: item[0],
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
    Format("<i>Например: 1000 или 1500.50</i>"),
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
        item_id_getter=lambda item: item[0],
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
        Const("🔗 Поделиться сделкой"),
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
    Const("🔍 <b>Детали твоего объявления</b>"),
    Format("""
📅 <b>Предложение:</b> {shift_date} {shift_time} ПРМ
💰 <b>Оплата:</b> {price} р. {payment_info}

📅 <b>Создано:</b> {created_at}"""),
    Row(
        Button(
            Const("✋🏻 Отменить"),
            id="cancel_exchange",
            on_click=on_exchange_cancel,
        ),
        Button(Const("🔄 Обновить"), id="refresh_exchange_detail"),
    ),
    SwitchInlineQueryChosenChatButton(
        Const("🔗 Поделиться сделкой"),
        query=Format("{deeplink}"),
        allow_user_chats=True,
        allow_group_chats=True,
        allow_channel_chats=False,
        allow_bot_chats=False,
        id="exchange_deeplink",
    ),
    SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.sell),
    getter=exchange_sell_detail_getter,
    state=Exchanges.sell_detail,
)


async def on_start(_on_start: Any, dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        dialog_manager: Менеджер диалога
    """
    day_filter_checkbox: ManagedRadio = dialog_manager.find("day_filter")
    await day_filter_checkbox.set_checked("all")

    shift_filter_checkbox: ManagedRadio = dialog_manager.find("shift_filter")
    await shift_filter_checkbox.set_checked("all")

    date_sort_toggle: ManagedToggle = dialog_manager.find("date_sort")
    await date_sort_toggle.set_checked("nearest")

    price_sort_toggle: ManagedToggle = dialog_manager.find("price_sort")
    await price_sort_toggle.set_checked("cheap")


exchanges_dialog = Dialog(
    exchanges_window,
    exchange_buy_window,
    exchange_sell_window,
    exchange_my_window,
    # Окна продажи смены
    sell_date_select_window,
    sell_hours_select_window,
    sell_time_input_window,
    sell_price_input_window,
    sell_payment_timing_window,
    sell_payment_date_window,
    sell_confirmation_window,
    exchange_buy_detail_window,
    exchange_sell_detail_window,
    # Настройки покупок
    buy_settings_window,
    buy_filters_day_window,
    buy_filters_shift_window,
    # Настройки продаж
    sell_settings_window,
    on_start=on_start,
)

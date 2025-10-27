"""Генерация окон для биржи подмен."""

import operator
from typing import Any

from aiogram import F
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Checkbox,
    ManagedRadio,
    ManagedToggle,
    Row,
    ScrollingGroup,
    Select,
    SwitchInlineQueryChosenChatButton,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.exchanges.exchanges import (
    finish_exchanges_dialog,
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
    on_exchange_buy,
    on_exchange_buy_selected,
    on_exchange_sell_selected,
    on_exchange_type_selected,
    on_my_exchange_selected,
    on_private_change,
    on_restore_exchange,
)
from tgbot.dialogs.getters.common.exchanges.exchanges import (
    edit_offer_date_getter,
    exchange_buy_detail_getter,
    exchange_buy_getter,
    exchange_sell_detail_getter,
    exchange_sell_getter,
    my_detail_getter,
    my_exchanges,
)
from tgbot.dialogs.menus.common.exchanges.settings import (
    buy_filters_day_window,
    buy_filters_shift_window,
    buy_settings_window,
    sell_settings_window,
)
from tgbot.dialogs.states.common.exchanges import Exchanges
from tgbot.dialogs.widgets.buttons import HOME_BTN
from tgbot.dialogs.widgets.calendars import RussianCalendar
from tgbot.dialogs.widgets.exchange_calendar import ExchangeCalendar

menu_window = Window(
    Const("🎭 <b>Биржа подмен</b>"),
    Format("""
Здесь ты можешь обменять свои рабочие часы, либо взять чужие"""),
    Row(
        SwitchTo(Const("📈 Купить"), id="buy", state=Exchanges.buy),
        SwitchTo(Const("📉 Продать"), id="sell", state=Exchanges.sell),
    ),
    SwitchTo(Const("🗳 Мои сделки"), id="my", state=Exchanges.my),
    SwitchTo(Const("💸 Создать предложение"), id="create", state=Exchanges.create),
    SwitchTo(Const("📊 Статистика"), id="stats", state=Exchanges.stats),
    Row(
        Button(Const("↩️ Назад"), id="back", on_click=finish_exchanges_dialog), HOME_BTN
    ),
    state=Exchanges.menu,
)

buy_window = Window(
    Const("📈 <b>Биржа: Покупка часов</b>"),
    Format("""
Здесь ты можешь найти и купить смены, которые продают другие сотрудники.

💰 <b>Доступно предложений:</b> {exchanges_length}"""),
    Format(
        "\n🔍 <i>Нажми на предложение для просмотра деталей</i>", when="has_exchanges"
    ),
    Format(
        "\n📭 <i>Пока никто не продает смены</i>",
        when=~F["has_exchanges"],
    ),
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


sell_window = Window(
    Const("📉 <b>Биржа: Продажа часов</b>"),
    Format("""
Здесь ты можешь найти людей, которые хотят купить смены, и продать им свои часы.

💰 <b>Запросы на покупку:</b> {buy_requests_length}"""),
    Format(
        "\n🔍 <i>Нажми на запрос для просмотра деталей</i>", when="has_buy_requests"
    ),
    Format(
        "\n📭 <i>Пока никто не ищет смены для покупки</i>",
        when=~F["has_buy_requests"],
    ),
    ScrollingGroup(
        Select(
            Format("{item[time]}, {item[date]} | {item[price]} р."),
            id="buy_request_select",
            items="available_buy_requests",
            item_id_getter=lambda item: item["id"],
            on_click=on_exchange_sell_selected,
        ),
        width=1,
        height=10,
        hide_on_single_page=True,
        id="buy_request_scrolling",
        when="has_buy_requests",
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

sell_detail = Window(
    Const("🔍 <b>Детали сделки</b>"),
    Format("""
{exchange_info}

👤 <b>Покупатель:</b> {buyer_name}
💳 <b>Оплата:</b> {payment_info}"""),
    Button(Const("✅ Продать"), id="accept_buy_request", on_click=on_exchange_buy),
    SwitchInlineQueryChosenChatButton(
        Const("🔗 Поделиться"),
        query=Format("{deeplink}"),
        allow_user_chats=True,
        allow_group_chats=True,
        allow_channel_chats=False,
        allow_bot_chats=False,
        id="buy_request_deeplink",
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.sell), HOME_BTN),
    getter=exchange_sell_detail_getter,
    state=Exchanges.sell_detail,
)

buy_detail_window = Window(
    Const("🔍 <b>Детали сделки</b>"),
    Format("""
{exchange_info}

👤 <b>Продавец:</b> {seller_name}
💳 <b>Оплата:</b> {payment_info}"""),
    Format(
        """
📝 <b>Комментарий:</b>
<blockquote expandable>{comment}</blockquote>""",
        when="comment",
    ),
    Button(Const("✅ Купить"), id="apply", on_click=on_exchange_buy),
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

create_window = Window(
    Const("<b>Выбери тип предложения</b>"),
    Const("""
<blockquote><b>📈 Купить</b> - Предложение о покупке часов тобой
Твои коллеги увидят предложение в разделе <b>📉 Продать</b></blockquote>

<blockquote><b>📉 Продать</b> - Предложение о продаже твоих часов
Твои коллеги увидят предложение в разделе <b>📈 Купить</b></blockquote>"""),
    Select(
        Format("{item[1]}"),
        id="exchange_type",
        items=[
            ("buy", "📈 Купить"),
            ("sell", "📉 Продать"),
        ],
        item_id_getter=operator.itemgetter(0),
        on_click=on_exchange_type_selected,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="cancel", state=Exchanges.menu),
        HOME_BTN,
    ),
    state=Exchanges.create,
)

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
📊 <b>Статус:</b> {status}

{exchange_info}"""),
    Format(
        """
👤 <b>Вторая сторона:</b> {other_party_name}""",
        when="has_other_party",
    ),
    Format(
        """
💳 <b>Оплата:</b> {payment_info}
💸 <b>Оплачено:</b> {'✅ Да' if is_paid else '❌ Нет'}""",
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
    Checkbox(
        Const("🫣 Приватная"),
        Const("👀 Публичная"),
        id="offer_private_status",
        on_state_changed=on_private_change,
        when=F["is_active"],
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
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Exchanges.edit_offer), HOME_BTN),
    state=Exchanges.edit_offer_comment,
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
    menu_window,
    buy_window,
    sell_window,
    create_window,
    my_window,
    buy_detail_window,
    sell_detail,
    my_detail_window,
    # Настройки покупок
    buy_settings_window,
    buy_filters_day_window,
    buy_filters_shift_window,
    # Настройки продаж
    sell_settings_window,
    # Редактирование сделки
    offer_edit_window,
    edit_offer_date_window,
    edit_offer_date_time_window,
    edit_offer_price_window,
    edit_offer_payment_timing_window,
    edit_offer_payment_date_window,
    edit_offer_comment_window,
    on_start=on_start,
)

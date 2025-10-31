"""Генерация диалогов для подписок на биржу."""

from aiogram import F
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Checkbox,
    Group,
    Multiselect,
    Radio,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.exchanges.subscriptions import (
    finish_subscriptions_dialog,
    on_confirm_subscription,
    on_create_subscription,
    on_criteria_next,
    on_delete_subscription,
    on_price_input,
    on_subscription_selected,
    on_toggle_subscription,
)
from tgbot.dialogs.getters.common.exchanges.subscriptions import (
    subscription_create_confirmation_getter,
    subscription_create_criteria_getter,
    subscription_create_date_getter,
    subscription_create_price_getter,
    subscription_create_time_getter,
    subscription_detail_getter,
    subscriptions_getter,
)
from tgbot.dialogs.states.common.exchanges import ExchangesSub
from tgbot.dialogs.widgets.buttons import HOME_BTN

menu_window = Window(
    Const("🔔 <b>Подписки</b>"),
    Format("""
Здесь ты можешь управлять подписками на новые обмены. Когда появится обмен, соответствующий твоим критериям, тебе придет уведомление.

📊 <b>Активных подписок:</b> {active_subscriptions_count}
📊 <b>Всего подписок:</b> {total_subscriptions_count}"""),
    Format(
        "\n🔍 <i>Нажми на подписку для просмотра деталей</i>",
        when="has_subscriptions",
    ),
    Format(
        "\n📭 <i>У тебя еще нет подписок</i>",
        when=~F["has_subscriptions"],
    ),
    ScrollingGroup(
        Select(
            Format("{item[name]} | {item[status]}"),
            id="subscription_select",
            items="subscriptions_list",
            item_id_getter=lambda item: item["id"],
            on_click=on_subscription_selected,
        ),
        width=1,
        height=8,
        hide_on_single_page=True,
        id="subscription_scrolling",
        when="has_subscriptions",
    ),
    Button(
        Const("➕ Новая подписка"),
        id="add_subscription",
        on_click=on_create_subscription,
    ),
    Row(
        Button(Const("🔄 Обновить"), id="refresh_subscriptions"),
    ),
    Row(
        Button(Const("↩️ Назад"), id="back", on_click=finish_subscriptions_dialog),
        HOME_BTN,
    ),
    getter=subscriptions_getter,
    state=ExchangesSub.menu,
)

# Детали подписки
sub_detail_window = Window(
    Const("🔍 <b>Детали подписки</b>"),
    Format("""
📝 <b>Название:</b> {subscription_name}
📈 <b>Тип обменов:</b> {exchange_type}
📋 <b>Критерии:</b>
{criteria_text}"""),
    Checkbox(
        Const("🟢 Активная"),
        Const("🟡 Выключена"),
        id="sub_status",
    ),
    Row(
        Button(
            Format("{toggle_text}"),
            id="toggle_subscription",
            on_click=on_toggle_subscription,
        ),
        Button(
            Const("🗑️ Удалить"),
            id="delete_subscription",
            on_click=on_delete_subscription,
        ),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangesSub.menu),
        HOME_BTN,
    ),
    getter=subscription_detail_getter,
    state=ExchangesSub.sub_detail,
)

# Выбор критериев подписки
subscription_create_criteria_window = Window(
    Const("🎯 <b>Шаг 1: Условия сделок</b>"),
    Format("""
<blockquote>📈 <b>Тип:</b> {selected_exchange_type}

{current_criteria_display}</blockquote>"""),
    Group(
        Multiselect(
            Format("✅ {item[1]}"),
            Format("☑️ {item[1]}"),
            id="criteria_toggles",
            item_id_getter=lambda item: item[0],
            items="criteria_options",
        ),
        width=2,
    ),
    Format(
        "\n💡 <i>Выберите критерии или оставь пустым для подписки на любые условия</i>",
    ),
    Row(
        Button(Const("⬅️ Отмена"), id="back", on_click=finish_subscriptions_dialog),
        Button(
            Const("➡️ Далее"),
            id="next_step",
            on_click=on_criteria_next,
        ),
    ),
    getter=subscription_create_criteria_getter,
    state=ExchangesSub.create_criteria,
)

# Настройка цены (если выбрана)
create_price_window = Window(
    Const("💰 <b>Шаг 2: Настройка минимальной цены</b>"),
    Format("""
<blockquote>📈 <b>Тип:</b> {exchange_type_display}
🎯 <b>Критерии:</b> {criteria_display}
{price_settings_display}</blockquote>"""),
    Format(
        "\n💡 Введи <b>минимальную цену в час</b> в рублях (или 0 для пропуска)",
    ),
    TextInput(
        id="price_input",
        type_factory=int,
        on_success=on_price_input,
    ),
    Row(
        SwitchTo(Const("⬅️ Назад"), id="back", state=ExchangesSub.create_criteria),
        Button(
            Const("➡️ Далее"),
            id="next_step",
            on_click=on_criteria_next,
        ),
    ),
    getter=subscription_create_price_getter,
    state=ExchangesSub.create_price,
)

# Настройка времени (если выбрана)
create_time_window = Window(
    Const("⏰ <b>Шаг 3: Выбор времени суток</b>"),
    Format("""
<blockquote>📈 <b>Тип:</b> {exchange_type_display}
🎯 <b>Критерии:</b> {criteria_display}
{current_settings_display}</blockquote>"""),
    Group(
        Radio(
            Format("🔘 {item[1]}"),
            Format("⚪ {item[1]}"),
            id="time_range",
            item_id_getter=lambda item: item[0],
            items="time_ranges",
        ),
        width=2,
    ),
    Format(
        "\n💡 Выбери временной диапазон",
    ),
    Row(
        Button(Const("⬅️ Назад"), id="back_step", on_click=on_criteria_next),
        Button(
            Const("➡️ Далее"),
            id="next_step",
            on_click=on_criteria_next,
        ),
    ),
    getter=subscription_create_time_getter,
    state=ExchangesSub.create_time,
)

# Настройка дат (если выбрана)
create_date_window = Window(
    Const("📅 <b>Шаг 4: Выбор дней недели</b>"),
    Format("""
<blockquote>📈 <b>Тип:</b> {exchange_type_display}
🎯 <b>Критерии:</b> {criteria_display}
{current_settings_display}</blockquote>"""),
    Group(
        Multiselect(
            Format("✅ {item[1]}"),
            Format("☑️ {item[1]}"),
            id="days_of_week",
            item_id_getter=lambda item: item[0],
            items="weekdays",
        ),
        width=2,
    ),
    Format(
        "\n💡 Выбери подходящие дни недели",
    ),
    Row(
        Button(Const("⬅️ Назад"), id="back_step", on_click=on_criteria_next),
        Button(
            Const("➡️ Далее"),
            id="next_step",
            on_click=on_criteria_next,
        ),
    ),
    getter=subscription_create_date_getter,
    state=ExchangesSub.create_date,
)


# Подтверждение создания
create_confirmation_window = Window(
    Const("✅ <b>Шаг 5: Подтверждение создания</b>"),
    Format("""
Проверь настройки подписки:

<blockquote>📈 <b>Тип:</b> {exchange_type}
🎯 <b>Критерии:</b>
{criteria_summary}</blockquote>"""),
    Row(
        Button(Const("✅ Создать"), id="confirm", on_click=on_confirm_subscription),
    ),
    Button(Const("⬅️ К настройкам"), id="back_step", on_click=on_criteria_next),
    Row(
        SwitchTo(Const("↩️ Назад"), id="cancel", state=ExchangesSub.menu),
        HOME_BTN,
    ),
    getter=subscription_create_confirmation_getter,
    state=ExchangesSub.create_confirmation,
)


exchanges_subscriptions_dialog = Dialog(
    menu_window,
    sub_detail_window,
    subscription_create_criteria_window,
    create_price_window,
    create_time_window,
    create_date_window,
    create_confirmation_window,
)

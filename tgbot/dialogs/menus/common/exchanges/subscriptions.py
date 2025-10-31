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
    on_confirm_subscription,
    on_create_subscription,
    on_criteria_next,
    on_delete_subscription,
    on_name_input,
    on_price_input,
    on_subscription_selected,
    on_toggle_subscription,
)
from tgbot.dialogs.getters.common.exchanges.subscriptions import (
    subscription_create_confirmation_getter,
    subscription_create_criteria_getter,
    subscription_create_date_getter,
    subscription_create_name_getter,
    subscription_create_price_getter,
    subscription_create_time_getter,
    subscription_create_type_getter,
    subscription_detail_getter,
    subscriptions_getter,
)
from tgbot.dialogs.states.common.exchanges import ExchangesSub
from tgbot.dialogs.widgets.buttons import HOME_BTN

# Главное меню подписок
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
    Row(
        Button(
            Const("➕ Новая подписка"),
            id="add_subscription",
            on_click=on_create_subscription,
        ),
        Button(Const("🔄 Обновить"), id="refresh_subscriptions"),
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=ExchangesSub.menu), HOME_BTN),
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

# Выбор типа подписки
create_type_window = Window(
    Const("➕ <b>Новая подписка</b>"),
    Const("""
Выберите тип обменов, на которые хотите подписаться:"""),
    Radio(
        Format("🔘 {item[1]}"),
        Format("⚪ {item[1]}"),
        id="exchange_type",
        item_id_getter=lambda item: item[0],
        items="exchange_types",
    ),
    Button(
        Const("➡️ Далее"),
        id="next_criteria",
        on_click=on_criteria_next,
        when="exchange_type_selected",
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangesSub.menu),
        HOME_BTN,
    ),
    getter=subscription_create_type_getter,
    state=ExchangesSub.create_type,
)

# Выбор критериев подписки
subscription_create_criteria_window = Window(
    Const("🎯 <b>Критерии подписки</b>"),
    Format("""
Выбери критерии для фильтрации обменов:

<b>Тип обменов:</b> {selected_exchange_type}"""),
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
    Row(
        SwitchTo(Const("⬅️ Назад"), id="back", state=ExchangesSub.create_type),
        Button(
            Const("➡️ Далее"),
            id="next_price",
            on_click=on_criteria_next,
            when="criteria_selected",
        ),
    ),
    getter=subscription_create_criteria_getter,
    state=ExchangesSub.create_criteria,
)

# Настройка цены (если выбрана)
create_price_window = Window(
    Const("💰 <b>Настройка цены</b>"),
    Format("""
Укажите диапазон цен для подписки:

<b>Выбранные критерии:</b>
{selected_criteria}"""),
    Format(
        "\n💰 <b>Минимальная цена:</b> {min_price} р.",
        when="min_price",
    ),
    Format(
        "\n💰 <b>Максимальная цена:</b> {max_price} р.",
        when="max_price",
    ),
    Format(
        "\n💡 <i>Введите минимальную цену (или 0 для пропуска):</i>",
        when="input_step_min",
    ),
    Format(
        "\n💡 <i>Введите максимальную цену (или 0 для пропуска):</i>",
        when="input_step_max",
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
            id="next_time",
            on_click=on_criteria_next,
            when="price_completed",
        ),
    ),
    getter=subscription_create_price_getter,
    state=ExchangesSub.create_price,
)

# Настройка времени (если выбрана)
create_time_window = Window(
    Const("⏰ <b>Настройка времени</b>"),
    Format("""
Выберите время суток для подписки:

<b>Выбранные критерии:</b>
{selected_criteria}"""),
    Radio(
        Format("🔘 {item[1]}"),
        Format("⚪ {item[1]}"),
        id="time_range",
        item_id_getter=lambda item: item[0],
        items="time_ranges",
    ),
    Row(
        SwitchTo(Const("⬅️ Назад"), id="back", state=ExchangesSub.create_price),
        Button(
            Const("➡️ Далее"),
            id="next_date",
            on_click=on_criteria_next,
            when="time_selected",
        ),
    ),
    getter=subscription_create_time_getter,
    state=ExchangesSub.create_time,
)

# Настройка дат (если выбрана)
create_date_window = Window(
    Const("📅 <b>Настройка дат</b>"),
    Format("""
Выберите дни недели для подписки:

<b>Выбранные критерии:</b>
{selected_criteria}"""),
    Multiselect(
        Format("✅ {item[1]}"),
        Format("☑️ {item[1]}"),
        id="days_of_week",
        item_id_getter=lambda item: item[0],
        items="weekdays",
    ),
    Row(
        SwitchTo(Const("⬅️ Назад"), id="back", state=ExchangesSub.create_time),
        Button(
            Const("➡️ Далее"),
            id="next_notifications",
            on_click=on_criteria_next,
            when="days_selected",
        ),
    ),
    getter=subscription_create_date_getter,
    state=ExchangesSub.create_date,
)


# Название подписки
create_name_window = Window(
    Const("📝 <b>Название подписки</b>"),
    Format("""
Дайте название вашей подписке для удобства:

<b>Краткое описание:</b>
{subscription_summary}"""),
    Format(
        "\n📝 <b>Текущее название:</b> {current_name}",
        when="current_name",
    ),
    Format("\n💡 <i>Введите название подписки:</i>"),
    TextInput(
        id="name_input",
        on_success=on_name_input,
    ),
    Button(
        Const("✨ Автоназвание"),
        id="auto_name",
        on_click=on_name_input,
    ),
    Row(
        SwitchTo(
            Const("⬅️ Назад"),
            id="back",
            state=ExchangesSub.create_date,
        ),
        Button(
            Const("➡️ К подтверждению"),
            id="next_confirmation",
            on_click=on_criteria_next,
            when="name_entered",
        ),
    ),
    getter=subscription_create_name_getter,
    state=ExchangesSub.create_name,
)

# Подтверждение создания
create_confirmation_window = Window(
    Const("✅ <b>Подтверждение создания</b>"),
    Format("""
Проверьте настройки подписки:

📝 <b>Название:</b> {subscription_name}
📈 <b>Тип обменов:</b> {exchange_type}
🎯 <b>Критерии:</b>
{criteria_summary}

🔔 <b>Уведомления:</b>
{notification_summary}"""),
    Row(
        Button(
            Const("✅ Создать подписку"), id="confirm", on_click=on_confirm_subscription
        ),
        SwitchTo(
            Const("✏️ Редактировать"),
            id="edit",
            state=ExchangesSub.create_name,
        ),
    ),
    Row(
        SwitchTo(Const("↩️ К подпискам"), id="cancel", state=ExchangesSub.menu),
        HOME_BTN,
    ),
    getter=subscription_create_confirmation_getter,
    state=ExchangesSub.create_confirmation,
)


exchanges_subscriptions_dialog = Dialog(
    menu_window,
    sub_detail_window,
    create_type_window,
    subscription_create_criteria_window,
    create_price_window,
    create_time_window,
    create_date_window,
    create_name_window,
    create_confirmation_window,
)

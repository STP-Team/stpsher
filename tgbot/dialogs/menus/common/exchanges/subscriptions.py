"""Генерация диалогов для подписок на биржу."""

from aiogram import F
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Cancel,
    Checkbox,
    Group,
    Multiselect,
    Radio,
    Row,
    ScrollingGroup,
    Select,
    SwitchInlineQueryChosenChatButton,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.exchanges.subscriptions import (
    on_clear_dates,
    on_confirm_subscription,
    on_create_subscription,
    on_criteria_next,
    on_date_selected,
    on_delete_subscription,
    on_price_input,
    on_seller_search_query,
    on_seller_selected,
    on_sub_status_click,
    on_subscription_selected,
)
from tgbot.dialogs.getters.common.exchanges.subscriptions import (
    subscription_create_confirmation_getter,
    subscription_create_criteria_getter,
    subscription_create_date_getter,
    subscription_create_price_getter,
    subscription_create_seller_results_getter,
    subscription_create_seller_search_getter,
    subscription_create_time_getter,
    subscription_create_type_getter,
    subscription_detail_getter,
    subscriptions_getter,
)
from tgbot.dialogs.states.common.exchanges import ExchangesSub
from tgbot.dialogs.widgets.buttons import HOME_BTN
from tgbot.dialogs.widgets.exchange_calendar import (
    SubscriptionCalendar,
)

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
        Cancel(Const("↩️ Назад"), id="close_sub"),
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
<b>Тип обменов:</b> {exchange_type}

🎯 <b>Критерии:</b>
{criteria_text}"""),
    Format("""
🔗 <b>Ссылка:</b> <code>{deeplink_url}</code>"""),
    Group(
        SwitchInlineQueryChosenChatButton(
            Const("🔗 Поделиться"),
            query=Format("{deeplink}"),
            allow_user_chats=True,
            allow_group_chats=True,
            allow_channel_chats=False,
            allow_bot_chats=False,
            id="subscription_deeplink",
        ),
        when=F["status"],
    ),
    Row(
        Checkbox(
            Const("🟢 Активная"),
            Const("🟡 Выключена"),
            id="sub_status",
            on_click=on_sub_status_click,
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

# Выбор типа обменов
subscription_create_type_window = Window(
    Const("📈 <b>Шаг 1: Тип обменов</b>"),
    Format("""\
Выберите тип обменов, на которые хотите подписаться:

💰 <b>Покупка</b> - получать уведомления о новых предложениях продажи смен
💼 <b>Продажа</b> - получать уведомления о новых запросах на покупку смен"""),
    Group(
        Radio(
            Format("🔘 {item[1]}"),
            Format("⚪ {item[1]}"),
            id="exchange_type",
            item_id_getter=lambda item: item[0],
            items="exchange_types",
        ),
        width=1,
    ),
    Format("\n💡 <i>Выберите интересующий вас тип обменов</i>"),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangesSub.menu),
        Button(
            Const("➡️ Далее"),
            id="next_step",
            on_click=on_criteria_next,
        ),
    ),
    getter=subscription_create_type_getter,
    state=ExchangesSub.create_type,
)

# Выбор критериев подписки
subscription_create_criteria_window = Window(
    Const("🎯 <b>Шаг 2: Условия сделок</b>"),
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
        SwitchTo(Const("↩️ Назад"), id="back", state=ExchangesSub.create_type),
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
    Const("💰 <b>Шаг 3: Настройка минимальной цены</b>"),
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
    Const("⏰ <b>Шаг 4: Выбор времени суток</b>"),
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
    Const("📅 <b>Шаг 5: Выбор конкретных дат</b>"),
    Format("""
<blockquote>📈 <b>Тип:</b> {exchange_type_display}
🎯 <b>Критерии:</b> {criteria_display}
{current_settings_display}</blockquote>"""),
    Format(
        "\n📅 <b>Выбранные даты:</b>\n{selected_dates_display}",
        when="has_selected_dates",
    ),
    SubscriptionCalendar(
        id="subscription_dates",
        on_click=on_date_selected,
    ),
    Format("\n💡 Нажми на дату в календаре, чтобы добавить/убрать её из подписки"),
    Format(
        "\n<i>👉 - выбранные даты, · · - дни со сменами</i>",
    ),
    Row(
        Button(Const("⬅️ Назад"), id="back_step", on_click=on_criteria_next),
        Button(
            Const("🗑️ Очистить"),
            id="clear_dates",
            on_click=on_clear_dates,
            when="has_selected_dates",
        ),
        Button(
            Const("➡️ Далее"),
            id="next_step",
            on_click=on_criteria_next,
        ),
    ),
    getter=subscription_create_date_getter,
    state=ExchangesSub.create_date,
)


# Поиск сотрудника
create_seller_search_window = Window(
    Const("👤 <b>Шаг: Выбор сотрудника</b>"),
    Format("""
<blockquote>📈 <b>Тип:</b> {exchange_type_display}
🎯 <b>Критерии:</b> {criteria_display}</blockquote>"""),
    Format("""
💡 Введи ФИО, ID пользователя или username сотрудника:

<i>Например: Иванов, 123456789, @username, username</i>"""),
    TextInput(
        id="seller_search_input",
        on_success=on_seller_search_query,
    ),
    Row(
        Button(Const("⬅️ Назад"), id="back_step", on_click=on_criteria_next),
        SwitchTo(Const("↩️ К меню"), id="cancel", state=ExchangesSub.menu),
    ),
    getter=subscription_create_seller_search_getter,
    state=ExchangesSub.create_seller,
)

# Результаты поиска сотрудника
create_seller_results_window = Window(
    Const("👤 <b>Результаты поиска</b>"),
    Format(
        """
По запросу "<code>{search_query}</code>" найдено: {total_found} сотрудников""",
        when="has_results",
    ),
    Format(
        """
❌ <b>Ничего не найдено</b>

По запросу "<code>{search_query}</code>" сотрудники не найдены.

Попробуйте:
• Проверить правильность написания
• Использовать только часть имени или фамилии
• Поискать по username без @
• Использовать числовой ID пользователя""",
        when=~F["has_results"],
    ),
    ScrollingGroup(
        Select(
            Format("{item[1]}"),
            id="seller_results",
            items="search_results",
            item_id_getter=lambda item: item[0],
            on_click=on_seller_selected,
        ),
        width=1,
        height=5,
        hide_on_single_page=True,
        id="seller_results_scroll",
        when="has_results",
    ),
    Row(
        SwitchTo(
            Const("🔄 Новый поиск"), id="new_search", state=ExchangesSub.create_seller
        ),
        Button(
            Const("➡️ Пропустить"),
            id="skip_seller",
            on_click=on_criteria_next,
            when=~F["has_results"],
        ),
    ),
    Row(
        Button(Const("⬅️ Назад"), id="back_step", on_click=on_criteria_next),
        SwitchTo(Const("↩️ К меню"), id="cancel", state=ExchangesSub.menu),
    ),
    getter=subscription_create_seller_results_getter,
    state=ExchangesSub.create_seller_results,
)


# Подтверждение создания
create_confirmation_window = Window(
    Const("✅ <b>Шаг 6: Подтверждение создания</b>"),
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
    subscription_create_type_window,
    subscription_create_criteria_window,
    create_price_window,
    create_time_window,
    create_date_window,
    create_seller_search_window,
    create_seller_results_window,
    create_confirmation_window,
)

"""Генерация диалога управления группой."""

import operator
from typing import Any

from aiogram import F
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import (
    Button,
    Checkbox,
    CurrentPage,
    FirstPage,
    Group,
    LastPage,
    ManagedRadio,
    NextPage,
    PrevPage,
    Radio,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format, List

from tgbot.dialogs.events.common.schedules import (
    do_nothing,
    next_day,
    next_month,
    prev_day,
    prev_month,
    today,
)
from tgbot.dialogs.events.common.search import on_trainee_click
from tgbot.dialogs.events.heads.group import (
    on_casino_click,
    on_game_casino_member_click,
    on_game_casino_toggle_all,
    on_member_role_change,
    on_member_schedule_mode_select,
    on_member_select,
)
from tgbot.dialogs.getters.common.schedules import group_schedule_getter
from tgbot.dialogs.getters.heads.group.game import (
    game_achievements_getter,
    game_balance_history_getter,
    game_casino_getter,
    game_products_getter,
    game_rating_getter,
    game_statistics_getter,
)
from tgbot.dialogs.getters.heads.group.members import (
    group_members_getter,
    member_access_level_getter,
    member_achievements_getter,
    member_info_getter,
    member_inventory_getter,
    member_kpi_getter,
    member_kpi_requirements_getter,
    member_salary_getter,
    member_schedule_getter,
)
from tgbot.dialogs.getters.heads.group.rating import get_rating_display_data
from tgbot.dialogs.states.head import HeadGroupSG
from tgbot.dialogs.widgets.buttons import HOME_BTN
from tgbot.misc.helpers import get_status_emoji

menu_window = Window(
    Const("""❤️ <b>Моя группа</b>
    
<i>Используй меню для выбора действия</i>"""),
    Row(
        SwitchTo(Const("📅 График"), id="files_processing", state=HeadGroupSG.schedule),
        SwitchTo(Const("🎖️ Рейтинг"), id="rating", state=HeadGroupSG.rating),
    ),
    Row(
        SwitchTo(Const("👥 Состав"), id="members", state=HeadGroupSG.members),
        SwitchTo(Const("🏮 Игра"), id="game", state=HeadGroupSG.game),
    ),
    HOME_BTN,
    state=HeadGroupSG.menu,
)

schedule_window = Window(
    Format("{group_text}"),
    Row(
        Button(
            Const("<"),
            id="prev_day",
            on_click=prev_day,
        ),
        Button(
            Format("📅 {date_display}"),
            id="current_date",
            on_click=do_nothing,
        ),
        Button(
            Const(">"),
            id="next_day",
            on_click=next_day,
        ),
    ),
    Button(
        Const("📍 Сегодня"),
        id="today",
        on_click=today,
        when=~F["is_today"],
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.menu),
        HOME_BTN,
    ),
    getter=group_schedule_getter,
    state=HeadGroupSG.schedule,
)

rating_window = Window(
    Format("{rating_text}"),
    Radio(
        Format("✓ {item[1]}"),
        Format("{item[1]}"),
        id="period_radio",
        item_id_getter=lambda x: x[0],
        items="periods",
    ),
    Radio(
        Format("✓ {item[1]}"),
        Format("{item[1]}"),
        id="normative_radio",
        item_id_getter=lambda x: x[0],
        items="normatives",
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.menu),
        HOME_BTN,
    ),
    getter=get_rating_display_data,
    state=HeadGroupSG.rating,
)

members_window = Window(
    Format("""👥 <b>Состав</b>

Сотрудников в группе: {total_members}"""),
    ScrollingGroup(
        Select(
            Format("{item[1]}"),
            id="group_members",
            items="members_list",
            item_id_getter=operator.itemgetter(0),
            on_click=on_member_select,
        ),
        width=2,
        height=5,
        hide_on_single_page=True,
        id="members_scroll",
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.menu),
        HOME_BTN,
    ),
    getter=group_members_getter,
    state=HeadGroupSG.members,
)

game_window = Window(
    Format("{statistics_text}"),
    Group(
        Row(
            SwitchTo(
                Const("🎯 Достижения"),
                id="achievements",
                state=HeadGroupSG.game_achievements,
            ),
            SwitchTo(
                Const("👏 Предметы"),
                id="products",
                state=HeadGroupSG.game_products,
            ),
        ),
        Row(
            SwitchTo(
                Const("💰 История группы"),
                id="balance_history",
                state=HeadGroupSG.game_balance_history,
            ),
            SwitchTo(
                Const("🎰 Казино"),
                id="casino",
                state=HeadGroupSG.game_casino,
            ),
        ),
        SwitchTo(
            Const("🎖️ Рейтинг"),
            id="rating",
            state=HeadGroupSG.game_rating,
        ),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.menu),
        HOME_BTN,
    ),
    getter=game_statistics_getter,
    state=HeadGroupSG.game,
)

game_achievements_window = Window(
    Const("""🎯 <b>Достижения группы</b>

История полученных достижений всех сотрудников группы
<i>Используй кнопки для выбора страницы</i>
"""),
    List(
        Format("""{pos}. <b>{item[1]}</b> - {item[7]}
<blockquote>🏅 Награда: {item[2]} баллов
📝 Описание: {item[3]}
💼 Должность: {item[4]}
🕒 Начисление: {item[5]}
📅 Получено: {item[6]}</blockquote>
"""),
        items="achievements",
        id="game_achievements_list",
        page_size=5,
    ),
    Row(
        FirstPage(
            scroll="game_achievements_list",
            text=Format("1"),
        ),
        PrevPage(
            scroll="game_achievements_list",
            text=Format("<"),
        ),
        CurrentPage(
            scroll="game_achievements_list",
            text=Format("{current_page1}"),
        ),
        NextPage(
            scroll="game_achievements_list",
            text=Format(">"),
        ),
        LastPage(
            scroll="game_achievements_list",
            text=Format("{target_page1}"),
        ),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.game),
        HOME_BTN,
    ),
    getter=game_achievements_getter,
    state=HeadGroupSG.game_achievements,
)

game_products_window = Window(
    Format("""🎒 <b>Инвентарь группы</b>

Все покупки сотрудников группы и их статус

Используй фильтры для поиска нужных предметов:
📦 - Готов к использованию
⏳ - На проверке
🔒 - Не осталось использований

<i>Всего предметов приобретено: {total_bought}</i>
<i>Показано: {total_shown}</i>"""),
    ScrollingGroup(
        Select(
            Format("{item[1]}"),
            id="game_inventory_product",
            items="products",
            item_id_getter=operator.itemgetter(0),
        ),
        width=2,
        height=3,
        hide_on_single_page=True,
        id="game_inventory_scroll",
    ),
    Radio(
        Format("🔘 {item[1]}"),
        Format("⚪️ {item[1]}"),
        id="game_inventory_filter",
        item_id_getter=operator.itemgetter(0),
        items=[
            ("all", "📋 Все"),
            ("stored", f"{get_status_emoji('stored')}"),
            ("review", f"{get_status_emoji('review')}"),
            ("used_up", f"{get_status_emoji('used_up')}"),
        ],
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.game),
        HOME_BTN,
    ),
    getter=game_products_getter,
    state=HeadGroupSG.game_products,
)

game_balance_history_window = Window(
    Const("""💰 <b>История баланса группы</b>

Последние 100 транзакций группы
<i>Используй кнопки для выбора страницы</i>
"""),
    List(
        Format("""{pos}. {item[1]}
<blockquote>💵 Сумма: <b>{item[2]}</b> баллов
📋 Тип: {item[3]}
📅 Дата: {item[4]}
📝 Описание: {item[5]}</blockquote>
"""),
        items="history",
        id="game_history_list",
        page_size=5,
    ),
    Row(
        FirstPage(
            scroll="game_history_list",
            text=Format("1"),
        ),
        PrevPage(
            scroll="game_history_list",
            text=Format("<"),
        ),
        CurrentPage(
            scroll="game_history_list",
            text=Format("{current_page1}"),
        ),
        NextPage(
            scroll="game_history_list",
            text=Format(">"),
        ),
        LastPage(
            scroll="game_history_list",
            text=Format("{target_page1}"),
        ),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.game),
        HOME_BTN,
    ),
    getter=game_balance_history_getter,
    state=HeadGroupSG.game_balance_history,
)

game_casino_window = Window(
    Format("""🎰 <b>Управление казино</b>

Здесь ты можешь управлять доступом к казино для каждого сотрудника

🟢 - Казино доступно
🔴 - Казино недоступно

<i>Всего сотрудников: {total_members}</i>
<i>Казино доступно: {casino_enabled_count}</i>"""),
    Button(
        Const("🔄 Переключить для всех"),
        id="toggle_all_casino",
        on_click=on_game_casino_toggle_all,
    ),
    ScrollingGroup(
        Select(
            Format("{item[1]}"),
            id="game_casino_members",
            items="members",
            item_id_getter=operator.itemgetter(0),
            on_click=on_game_casino_member_click,
        ),
        width=2,
        height=5,
        hide_on_single_page=True,
        id="game_casino_scroll",
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.game),
        HOME_BTN,
    ),
    getter=game_casino_getter,
    state=HeadGroupSG.game_casino,
)

game_rating_window = Window(
    Format("{rating_text}"),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.game),
        HOME_BTN,
    ),
    getter=game_rating_getter,
    state=HeadGroupSG.game_rating,
)

member_details_window = Window(
    Format("{user_info}"),
    Group(
        Row(
            SwitchTo(
                Const("📅 График"),
                id="files_processing",
                state=HeadGroupSG.member_schedule,
            ),
            SwitchTo(Const("🌟 Показатели"), id="kpi", state=HeadGroupSG.member_kpi),
        ),
        Row(
            SwitchTo(
                Const("🎯 Достижения"),
                id="achievements",
                state=HeadGroupSG.member_achievements,
            ),
            SwitchTo(
                Const("👏 Предметы"), id="products", state=HeadGroupSG.member_inventory
            ),
        ),
        Checkbox(
            Const("🟢 Казино"),
            Const("🔴 Казино"),
            id="member_casino_access",
            on_click=on_casino_click,
        ),
        SwitchTo(
            Const("🛡️ Уровень доступа"),
            id="access_level",
            state=HeadGroupSG.member_access_level,
        ),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.members),
        HOME_BTN,
    ),
    getter=member_info_getter,
    state=HeadGroupSG.member_details,
)

member_access_level_window = Window(
    Format("""<b>{selected_user_name}</b>

🛡️ <b>Уровень доступа</b>
Текущий уровень: {current_role_name}

Выбери уровень доступа из меню для назначения сотруднику"""),
    Group(
        Checkbox(
            Const("✅ Стажер"),
            Const("❌ Стажер"),
            id="is_trainee",
            on_click=on_trainee_click,
        ),
        Select(
            Format("{item[1]}"),
            id="member_access_level_select",
            item_id_getter=operator.itemgetter(0),
            items="roles",
            on_click=on_member_role_change,
        ),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.member_details),
        HOME_BTN,
    ),
    getter=member_access_level_getter,
    state=HeadGroupSG.member_access_level,
)

member_schedule_window = Window(
    Format("{schedule_text}"),
    Row(
        Button(
            Const("<"),
            id="prev_month",
            on_click=prev_month,
        ),
        Button(
            Format("{month_display}"),
            id="current_month",
            on_click=do_nothing,
        ),
        Button(
            Const(">"),
            id="next_month",
            on_click=next_month,
        ),
    ),
    Radio(
        Format("🔘 {item[1]}"),
        Format("⚪️ {item[1]}"),
        id="schedule_mode",
        item_id_getter=operator.itemgetter(0),
        items="mode_options",
        on_click=on_member_schedule_mode_select,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.member_details),
        HOME_BTN,
    ),
    getter=member_schedule_getter,
    state=HeadGroupSG.member_schedule,
)

member_kpi_window = Window(
    Format("{kpi_text}"),
    Row(
        SwitchTo(
            Const("🧮 Нормативы"),
            id="calculator",
            state=HeadGroupSG.member_kpi_requirements,
        ),
        SwitchTo(
            Const("💰 Зарплата"),
            id="salary",
            state=HeadGroupSG.member_kpi_salary,
        ),
    ),
    SwitchTo(Const("🔄 Обновить"), id="update", state=HeadGroupSG.member_kpi),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.member_details),
        HOME_BTN,
    ),
    getter=member_kpi_getter,
    state=HeadGroupSG.member_kpi,
)

member_kpi_requirements_window = Window(
    Format("{requirements_text}"),
    Row(
        SwitchTo(Const("🌟 Показатели"), id="kpi", state=HeadGroupSG.member_kpi),
        SwitchTo(
            Const("💰 Зарплата"),
            id="salary",
            state=HeadGroupSG.member_kpi_salary,
        ),
    ),
    SwitchTo(
        Const("🔄 Обновить"), id="update", state=HeadGroupSG.member_kpi_requirements
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.member_details),
        HOME_BTN,
    ),
    getter=member_kpi_requirements_getter,
    state=HeadGroupSG.member_kpi_requirements,
)

member_kpi_salary_window = Window(
    Format("{salary_text}"),
    Row(
        SwitchTo(Const("🌟 Показатели"), id="kpi", state=HeadGroupSG.member_kpi),
        SwitchTo(
            Const("🧮 Нормативы"),
            id="calculator",
            state=HeadGroupSG.member_kpi_requirements,
        ),
    ),
    SwitchTo(Const("🔄 Обновить"), id="update", state=HeadGroupSG.member_kpi_salary),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.member_details),
        HOME_BTN,
    ),
    getter=member_salary_getter,
    state=HeadGroupSG.member_kpi_salary,
)

member_achievements_window = Window(
    Format("""🎯 <b>Достижения</b>

<b>{user_name}</b>

История полученных достижений
<i>Всего получено: {total_achievements}</i>
"""),
    List(
        Format("""{pos}. <b>{item[1]}</b>
<blockquote>🏅 Награда: {item[2]} баллов
📝 Описание: {item[3]}
💼 Должность: {item[4]}
🕒 Начисление: {item[5]}
📅 Получено: {item[6]}</blockquote>
"""),
        items="achievements",
        id="member_achievements_list",
        page_size=3,
    ),
    Const("<i>Используй кнопки для выбора страницы или фильтров</i>"),
    Row(
        FirstPage(
            scroll="member_achievements_list",
            text=Format("1"),
        ),
        PrevPage(
            scroll="member_achievements_list",
            text=Format("<"),
        ),
        CurrentPage(
            scroll="member_achievements_list",
            text=Format("{current_page1}"),
        ),
        NextPage(
            scroll="member_achievements_list",
            text=Format(">"),
        ),
        LastPage(
            scroll="member_achievements_list",
            text=Format("{target_page1}"),
        ),
    ),
    Radio(
        Format("🔘 {item[1]}"),
        Format("⚪️ {item[1]}"),
        id="member_achievement_period_filter",
        item_id_getter=operator.itemgetter(0),
        items="period_radio_data",
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.member_details),
        HOME_BTN,
    ),
    getter=member_achievements_getter,
    state=HeadGroupSG.member_achievements,
)

member_inventory_window = Window(
    Format("""🎒 <b>Инвентарь</b>

<b>{user_name}</b>

Здесь можно увидеть все покупки сотрудника, их статус

Используй фильтры для поиска нужных предметов:
📦 - Готов к использованию
⏳ - На проверке
🔒 - Не осталось использований

<i>Всего предметов приобретено: {total_bought}</i>
<i>Показано: {total_shown}</i>"""),
    ScrollingGroup(
        Select(
            Format("{item[1]}"),
            id="member_inventory_product",
            items="products",
            item_id_getter=operator.itemgetter(0),
        ),
        width=2,
        height=3,
        hide_on_single_page=True,
        id="member_inventory_scroll",
    ),
    Radio(
        Format("🔘 {item[1]}"),
        Format("⚪️ {item[1]}"),
        id="member_inventory_filter",
        item_id_getter=operator.itemgetter(0),
        items=[
            ("all", "📋 Все"),
            ("stored", f"{get_status_emoji('stored')}"),
            ("review", f"{get_status_emoji('review')}"),
            ("used_up", f"{get_status_emoji('used_up')}"),
        ],
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.member_details),
        HOME_BTN,
    ),
    getter=member_inventory_getter,
    state=HeadGroupSG.member_inventory,
)


async def on_start(_on_start: Any, dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        dialog_manager: Менеджер диалога
    """
    # Фильтр рейтинга на "День"
    period_radio: ManagedRadio = dialog_manager.find("period_radio")
    await period_radio.set_checked("day")

    # Фильтр рейтинга на "Оценка"
    normative_radio: ManagedRadio = dialog_manager.find("normative_radio")
    await normative_radio.set_checked("csi")

    # Стандартный режим отображения графика на "Кратко"
    member_schedule_mode: ManagedRadio = dialog_manager.find("schedule_mode")
    await member_schedule_mode.set_checked("compact")

    # Фильтр достижений на "Все"
    member_achievement_period_filter: ManagedRadio = dialog_manager.find(
        "member_achievement_period_filter"
    )
    await member_achievement_period_filter.set_checked("all")

    # Фильтр инвентаря на "Все"
    member_inventory_filter: ManagedRadio = dialog_manager.find(
        "member_inventory_filter"
    )
    await member_inventory_filter.set_checked("all")

    # Фильтр инвентаря группы на "Все"
    game_inventory_filter: ManagedRadio = dialog_manager.find("game_inventory_filter")
    await game_inventory_filter.set_checked("all")


head_group_dialog = Dialog(
    menu_window,
    schedule_window,
    rating_window,
    members_window,
    game_window,
    # Game sub-windows
    game_achievements_window,
    game_products_window,
    game_balance_history_window,
    game_casino_window,
    game_rating_window,
    # Member detail windows
    member_details_window,
    member_access_level_window,
    member_schedule_window,
    member_kpi_window,
    member_kpi_requirements_window,
    member_kpi_salary_window,
    member_achievements_window,
    member_inventory_window,
    on_start=on_start,
)

"""Генерация общих функций для поиска."""

from typing import Any

from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Checkbox,
    Group,
    ManagedRadio,
    Radio,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.callbacks.common.schedule_functions import (
    do_nothing,
    next_month,
    prev_month,
)
from tgbot.dialogs.events.common.filters import on_filter_change
from tgbot.dialogs.events.common.search import (
    close_search_dialog,
    on_back_to_menu,
    on_casino_change,
    on_role_change,
    on_schedule_mode_select,
    on_search_query,
    on_user_select,
)
from tgbot.dialogs.getters.common.search import (
    search_access_level_getter,
    search_heads_getter,
    search_kpi_getter,
    search_kpi_requirements_getter,
    search_results_getter,
    search_salary_getter,
    search_schedule_getter,
    search_specialists_getter,
    search_user_info_getter,
)
from tgbot.dialogs.states.common.search import Search

menu_window = Window(
    Format("""🕵🏻 <b>Поиск сотрудника</b>

<i>Выбери должность искомого человека или воспользуйся общим поиском</i>"""),
    Row(
        SwitchTo(
            Const("👤 Специалисты"),
            id="schedules",
            state=Search.specialists,
        ),
        SwitchTo(Const("👑 Руководители"), id="kpi", state=Search.heads),
    ),
    SwitchTo(Const("🕵🏻 Поиск"), id="game", state=Search.query),
    Button(Const("↩️ Назад"), id="menu", on_click=close_search_dialog),
    state=Search.menu,
)

specialists_window = Window(
    Format(
        """👤 Специалисты

Найдено специалистов: {total_specialists}""",
    ),
    ScrollingGroup(
        Select(
            Format("{item[1]}"),
            id="search_specialists",
            items="specialists_list",
            item_id_getter=lambda item: item[0],
            on_click=on_user_select,
        ),
        width=2,
        height=5,
        hide_on_single_page=True,
        id="search_scroll",
    ),
    Row(
        Radio(
            Format("🔘 {item[1]}"),
            Format("⚪️ {item[1]}"),
            id="search_divisions",
            item_id_getter=lambda item: item[0],
            items="division_options",
            on_click=on_filter_change,
        ),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="menu", state=Search.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_search_dialog),
    ),
    getter=search_specialists_getter,
    state=Search.specialists,
)

heads_window = Window(
    Format(
        """👑 Руководители

Найдено руководителей: {total_heads}""",
    ),
    ScrollingGroup(
        Select(
            Format("{item[1]}"),
            id="search_heads",
            items="heads_list",
            item_id_getter=lambda item: item[0],
            on_click=on_user_select,
        ),
        width=2,
        height=5,
        hide_on_single_page=True,
        id="search_scroll",
    ),
    Row(
        Radio(
            Format("🔘 {item[1]}"),
            Format("⚪️ {item[1]}"),
            id="search_divisions",
            item_id_getter=lambda item: item[0],
            items="division_options",
            on_click=on_filter_change,
        ),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="menu", state=Search.query),
        Button(Const("🏠 Домой"), id="home", on_click=close_search_dialog),
    ),
    getter=search_heads_getter,
    state=Search.heads,
)

query_window = Window(
    Format("""🕵🏻 Поиск сотрудника

Введи:
• Часть имени/фамилии или полное ФИО
• ID пользователя (число)
• Username Telegram (@username или username)

<i>Например: Иванов, 123456789, @username, username</i>"""),
    TextInput(id="search_query", on_success=on_search_query),
    SwitchTo(Const("↩️ Назад"), id="back", state=Search.menu),
    state=Search.query,
)

query_results_window = Window(
    Format("""🔍 <b>Результаты поиска</b>

По запросу "<code>{search_query}</code>" найдено: {total_found} сотрудников"""),
    ScrollingGroup(
        Select(
            Format("{item[1]}"),
            id="search_results",
            items="search_results",
            item_id_getter=lambda item: item[0],
            on_click=on_user_select,
        ),
        width=1,
        height=5,
        hide_on_single_page=True,
        id="search_results_scroll",
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Search.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_search_dialog),
    ),
    getter=search_results_getter,
    state=Search.query_results,
)

query_no_results_window = Window(
    Format("""❌ <b>Ничего не найдено</b>

По запросу "<code>{search_query}</code>" сотрудники не найдены.

Попробуйте:
• Проверить правильность написания
• Использовать только часть имени или фамилии
• Поискать по username без @
• Использовать числовой ID пользователя"""),
    SwitchTo(Const("🔄 Новый поиск"), id="new_search", state=Search.query),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Search.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_search_dialog),
    ),
    getter=search_results_getter,
    state=Search.query_no_results,
)

details_window = Window(
    Format("{user_info}"),
    Group(
        Row(
            SwitchTo(
                Const("📅 График"), id="schedule", state=Search.details_schedule_window
            ),
            SwitchTo(Const("🌟 Показатели"), id="kpi", state=Search.details_kpi_window),
        ),
        Checkbox(
            Const("🟢 Казино"),
            Const("🔴 Казино"),
            id="casino_access",
            on_state_changed=on_casino_change,
            when="user_casino_access",
        ),
        SwitchTo(
            Const("🛡️ Уровень доступа"),
            id="access_level",
            state=Search.details_access_level_window,
        ),
        when="is_head",
    ),
    Group(
        Row(
            SwitchTo(
                Const("📅 График"), id="schedule", state=Search.details_schedule_window
            ),
            SwitchTo(
                Const("🛡️ Уровень доступа"),
                id="access_level",
                state=Search.details_access_level_window,
            ),
        ),
        when="is_mip",
    ),
    Group(
        Row(
            SwitchTo(
                Const("📅 График"), id="schedule", state=Search.details_schedule_window
            ),
            SwitchTo(Const("🌟 Показатели"), id="kpi", state=Search.details_kpi_window),
        ),
        Checkbox(
            Const("🟢 Казино"),
            Const("🔴 Казино"),
            id="casino_access",
            on_state_changed=on_casino_change,
            when="user_casino_access",
        ),
        SwitchTo(
            Const("🛡️ Уровень доступа"),
            id="access_level",
            state=Search.details_access_level_window,
        ),
        when="is_root",
    ),
    Row(
        Button(Const("↩️ Назад"), id="back", on_click=on_back_to_menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_search_dialog),
    ),
    getter=search_user_info_getter,
    state=Search.details_window,
)


details_access_level_window = Window(
    Format("""🛡️ <b>Уровень доступа</b>

<b>{selected_user_name}</b>
Текущая роль: {current_role_name}

Выбери уровень доступа из меню для назначения сотруднику"""),
    Group(
        Select(
            Format("{item[1]}"),
            id="access_level_select",
            item_id_getter=lambda item: item[0],
            items="roles",
            on_click=on_role_change,
        ),
        width=2,
        when="is_mip",
    ),
    Group(
        Checkbox(
            Const("✅ Стажер"),
            Const("❌ Стажер"),
            id="is_trainee",
        ),
        Select(
            Format("{item[1]}"),
            id="access_level_select",
            item_id_getter=lambda item: item[0],
            items="roles",
            on_click=on_role_change,
        ),
        when="is_head",
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Search.details_window),
        Button(Const("🏠 Домой"), id="home", on_click=close_search_dialog),
    ),
    getter=search_access_level_getter,
    state=Search.details_access_level_window,
)


details_schedule_window = Window(
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
        item_id_getter=lambda item: item[0],
        items="mode_options",
        on_click=on_schedule_mode_select,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Search.details_window),
        Button(Const("🏠 Домой"), id="home", on_click=close_search_dialog),
    ),
    getter=search_schedule_getter,
    state=Search.details_schedule_window,
)


details_kpi_window = Window(
    Format("{kpi_text}"),
    Row(
        SwitchTo(
            Const("🧮 Нормативы"),
            id="calculator",
            state=Search.details_kpi_requirements_window,
        ),
        SwitchTo(
            Const("💰 Зарплата"),
            id="salary",
            state=Search.details_kpi_salary_window,
        ),
    ),
    SwitchTo(Const("🔄 Обновить"), id="update", state=Search.details_kpi_window),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Search.details_window),
        Button(Const("🏠 Домой"), id="home", on_click=close_search_dialog),
    ),
    getter=search_kpi_getter,
    state=Search.details_kpi_window,
)


details_kpi_requirements_window = Window(
    Format("{requirements_text}"),
    Row(
        SwitchTo(Const("🌟 Показатели"), id="kpi", state=Search.details_kpi_window),
        SwitchTo(
            Const("💰 Зарплата"),
            id="salary",
            state=Search.details_kpi_salary_window,
        ),
    ),
    SwitchTo(
        Const("🔄 Обновить"), id="update", state=Search.details_kpi_requirements_window
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Search.details_window),
        Button(Const("🏠 Домой"), id="home", on_click=close_search_dialog),
    ),
    getter=search_kpi_requirements_getter,
    state=Search.details_kpi_requirements_window,
)


details_kpi_salary_window = Window(
    Format("{salary_text}"),
    Row(
        SwitchTo(Const("🌟 Показатели"), id="kpi", state=Search.details_kpi_window),
        SwitchTo(
            Const("🧮 Нормативы"),
            id="calculator",
            state=Search.details_kpi_requirements_window,
        ),
    ),
    SwitchTo(Const("🔄 Обновить"), id="update", state=Search.details_kpi_salary_window),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Search.details_window),
        Button(Const("🏠 Домой"), id="home", on_click=close_search_dialog),
    ),
    getter=search_salary_getter,
    state=Search.details_kpi_salary_window,
)


async def on_start(_on_start: Any, dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        dialog_manager: Менеджер диалога
    """
    # Фильтр поиска по направлению на "Все"
    search_divisions: ManagedRadio = dialog_manager.find("search_divisions")
    await search_divisions.set_checked("all")

    # Стандартный режим отображения графика на "Кратко"
    schedule_mode: ManagedRadio = dialog_manager.find("schedule_mode")
    await schedule_mode.set_checked("compact")


search_dialog = Dialog(
    menu_window,
    specialists_window,
    heads_window,
    query_window,
    query_results_window,
    query_no_results_window,
    details_window,
    details_access_level_window,
    details_schedule_window,
    details_kpi_window,
    details_kpi_requirements_window,
    details_kpi_salary_window,
    on_start=on_start,
)

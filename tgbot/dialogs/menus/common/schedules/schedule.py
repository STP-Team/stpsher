"""Генерация диалога для графиков."""

from typing import Any

from aiogram import F
from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import (
    Button,
    ManagedRadio,
    Radio,
    Row,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.events.common.schedules import (
    close_schedules_dialog,
    do_nothing,
    next_day,
    next_month,
    on_date_selected,
    prev_day,
    prev_month,
    today,
)
from tgbot.dialogs.getters.common.schedules import (
    duty_schedule_getter,
    group_schedule_getter,
    head_schedule_getter,
    schedules_getter,
    user_schedule_getter,
)
from tgbot.dialogs.menus.common.schedules.exchanges import (
    exchange_buy_detail_window,
    exchange_buy_window,
    exchange_my_window,
    exchange_sell_detail_window,
    exchange_sell_window,
    exchanges_window,
    sell_confirmation_window,
    sell_date_select_window,
    sell_hours_select_window,
    sell_payment_date_window,
    sell_payment_timing_window,
    sell_price_input_window,
    sell_time_input_window,
)
from tgbot.dialogs.states.common.schedule import Schedules
from tgbot.dialogs.widgets import RussianCalendar

menu_window = Window(
    Format("""<b>📅 Меню графиков</b>

Здесь ты найдешь все, что связано с графиками"""),
    Row(
        SwitchTo(
            Const("👔 Мой график"),
            id="schedule_my",
            state=Schedules.my,
        ),
        SwitchTo(
            Const("❤️ Моя группа"),
            id="schedule_group",
            state=Schedules.group,
        ),
    ),
    Row(
        SwitchTo(
            Const("👮‍♂️ Дежурные"),
            id="schedule_duties",
            state=Schedules.duties,
        ),
        SwitchTo(
            Const("👑 Руководители"),
            id="schedule_heads",
            state=Schedules.heads,
        ),
    ),
    SwitchTo(
        Const("🎭 Биржа подмен"),
        id="exchanges",
        state=Schedules.exchanges,
        when="is_user",
    ),
    Button(Const("↩️ Назад"), id="home", on_click=close_schedules_dialog),
    getter=schedules_getter,
    state=Schedules.menu,
)

my_window = Window(
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
    Row(
        Radio(
            Format("🔘 {item[1]}"),
            Format("⚪️ {item[1]}"),
            id="schedule_mode",
            item_id_getter=lambda item: item[0],
            items="mode_options",
        ),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="to_schedules", state=Schedules.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_schedules_dialog),
    ),
    getter=user_schedule_getter,
    state=Schedules.my,
)


duties_window = Window(
    Format("{duties_text}"),
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
    Row(
        Button(
            Const("📍 Сегодня"),
            id="today",
            on_click=today,
            when=~F["is_today"],
        ),
        SwitchTo(
            Const("📆 Выбор дня"),
            id="calendar",
            state=Schedules.duties_calendar,
        ),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="to_schedules", state=Schedules.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_schedules_dialog),
    ),
    getter=duty_schedule_getter,
    state=Schedules.duties,
)

group_window = Window(
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
    Row(
        Button(
            Const("📍 Сегодня"),
            id="today",
            on_click=today,
            when=~F["is_today"],
        ),
        SwitchTo(
            Const("📆 Выбор дня"),
            id="calendar",
            state=Schedules.group_calendar,
        ),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_schedules_dialog),
    ),
    getter=group_schedule_getter,
    state=Schedules.group,
)

heads_window = Window(
    Format("{heads_text}"),
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
    Row(
        Button(
            Const("📍 Сегодня"),
            id="today",
            on_click=today,
            when=~F["is_today"],
        ),
        SwitchTo(
            Const("📆 Выбор дня"),
            id="calendar",
            state=Schedules.heads_calendar,
        ),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_schedules_dialog),
    ),
    getter=head_schedule_getter,
    state=Schedules.heads,
)

# Окна календарей
duties_calendar_window = Window(
    Const("<b>📅 Выбор даты для дежурных</b>\n\nВыберите дату из календаря:"),
    RussianCalendar(id="duties_calendar", on_click=on_date_selected),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.duties),
        Button(Const("🏠 Домой"), id="home", on_click=close_schedules_dialog),
    ),
    state=Schedules.duties_calendar,
)

group_calendar_window = Window(
    Const("<b>📅 Выбор даты для группы</b>\n\nВыберите дату из календаря:"),
    RussianCalendar(id="group_calendar", on_click=on_date_selected),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.group),
        Button(Const("🏠 Домой"), id="home", on_click=close_schedules_dialog),
    ),
    state=Schedules.group_calendar,
)

heads_calendar_window = Window(
    Const("<b>📅 Выбор даты для руководителей</b>\n\nВыберите дату из календаря:"),
    RussianCalendar(id="heads_calendar", on_click=on_date_selected),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.heads),
        Button(Const("🏠 Домой"), id="home", on_click=close_schedules_dialog),
    ),
    state=Schedules.heads_calendar,
)


async def on_start(_on_start: Any, dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        dialog_manager: Менеджер диалога
    """
    # Стандартный режим отображения графика на "Кратко"
    schedule_mode: ManagedRadio = dialog_manager.find("schedule_mode")
    await schedule_mode.set_checked("compact")


schedules_dialog = Dialog(
    menu_window,
    my_window,
    group_window,
    duties_window,
    heads_window,
    duties_calendar_window,
    group_calendar_window,
    heads_calendar_window,
    exchanges_window,
    exchange_buy_window,
    exchange_sell_window,
    exchange_my_window,
    # Новые окна для процесса продажи смены
    sell_date_select_window,
    sell_hours_select_window,
    sell_time_input_window,
    sell_price_input_window,
    sell_payment_timing_window,
    sell_payment_date_window,
    sell_confirmation_window,
    exchange_buy_detail_window,
    exchange_sell_detail_window,
    on_start=on_start,
)

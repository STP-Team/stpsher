"""Генерация окон графиков для руководителей."""

from aiogram import F
from aiogram_dialog.widgets.kbd import (
    Button,
    Radio,
    Row,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.callbacks.common.schedule_functions import (
    clear_and_switch_to_duties,
    clear_and_switch_to_group,
    clear_and_switch_to_heads,
    clear_and_switch_to_my,
    do_nothing,
    next_day,
    next_month,
    prev_day,
    prev_month,
    today,
)
from tgbot.dialogs.callbacks.user_functions import (
    on_mode_select,
)
from tgbot.dialogs.getters.common.schedule import (
    duty_schedule_getter,
    group_schedule_getter,
    head_schedule_getter,
    user_schedule_getter,
)
from tgbot.dialogs.states.head import HeadSG

schedule_window = Window(
    Format("""<b>📅 Меню графиков</b>

Здесь ты найдешь все, что связано с графиками"""),
    Row(
        Button(
            Const("👔 Мой график"),
            id="schedule_my",
            on_click=clear_and_switch_to_my,
        ),
        Button(
            Const("❤️ Моя группа"),
            id="schedule_group",
            on_click=clear_and_switch_to_group,
        ),
    ),
    Row(
        Button(
            Const("👮‍♂️ Дежурные"),
            id="schedule_duties",
            on_click=clear_and_switch_to_duties,
        ),
        Button(
            Const("👑 Руководители"),
            id="schedule_heads",
            on_click=clear_and_switch_to_heads,
        ),
    ),
    SwitchTo(Const("↩️ Назад"), id="back_to_menu", state=HeadSG.menu),
    state=HeadSG.schedule,
)

schedule_my_window = Window(
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
            on_click=on_mode_select,
        ),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="to_schedules", state=HeadSG.schedule),
        SwitchTo(Const("🏠 Домой"), id="home", state=HeadSG.menu),
    ),
    getter=user_schedule_getter,
    state=HeadSG.schedule_my,
)


schedule_duties_window = Window(
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
    Button(
        Const("📍 Сегодня"),
        id="today",
        on_click=today,
        when=~F["is_today"],
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="to_schedules", state=HeadSG.schedule),
        SwitchTo(Const("🏠 Домой"), id="home", state=HeadSG.menu),
    ),
    getter=duty_schedule_getter,
    state=HeadSG.schedule_duties,
)

schedule_group_window = Window(
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
        SwitchTo(Const("↩️ Назад"), id="to_schedules", state=HeadSG.schedule),
        SwitchTo(Const("🏠 Домой"), id="home", state=HeadSG.menu),
    ),
    getter=group_schedule_getter,
    state=HeadSG.schedule_group,
)

schedule_heads_window = Window(
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
    Button(
        Const("📍 Сегодня"),
        id="today",
        on_click=today,
        when=~F["is_today"],
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="to_schedules", state=HeadSG.schedule),
        SwitchTo(Const("🏠 Домой"), id="home", state=HeadSG.menu),
    ),
    getter=head_schedule_getter,
    state=HeadSG.schedule_heads,
)

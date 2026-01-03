"""Генерация диалога для графиков."""

import operator
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

from tgbot.dialogs.events.common.exchanges.exchanges import start_exchanges_dialog
from tgbot.dialogs.events.common.schedules import (
    do_nothing,
    next_day,
    next_month,
    on_date_selected,
    open_my_exchanges,
    prev_day,
    prev_month,
    switch_to_calendar_view,
    switch_to_text_view,
    today,
)
from tgbot.dialogs.getters.common.schedules import (
    duty_schedule_getter,
    group_schedule_getter,
    head_schedule_getter,
    my_schedule_calendar_getter,
    schedules_getter,
    tutors_schedule_getter,
    user_schedule_getter,
)
from tgbot.dialogs.states.common.schedule import Schedules
from tgbot.dialogs.widgets import RussianCalendar
from tgbot.dialogs.widgets.buttons import HOME_BTN
from tgbot.dialogs.widgets.exchange_calendar import ExchangeCalendar

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
        Const("🎓 Наставники"),
        id="schedule_tutors",
        state=Schedules.tutors,
        when=F["tutor_access"],
    ),
    Button(
        Const("🎭 Биржа подмен"),
        id="exchanges",
        on_click=start_exchanges_dialog,
        when=~F["exchange_banned"],
    ),
    HOME_BTN,
    getter=schedules_getter,
    state=Schedules.menu,
)

my_window = Window(
    Format(
        "{schedule_text}\n<tg-spoiler><i>Данные из файла <b>{file_name}</b> от <b>{upload_date}</b>\nМеню обновлено в <b>{current_time_str}</b></i></tg-spoiler>"
    ),
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
    Button(Const("🗳 Мои сделки"), id="my_exchanges", on_click=open_my_exchanges),
    Button(
        Const("📅 Вид календаря"), id="calendar_view", on_click=switch_to_calendar_view
    ),
    Row(
        Radio(
            Format("🔘 {item[1]}"),
            Format("⚪️ {item[1]}"),
            id="my_schedule_mode",
            item_id_getter=operator.itemgetter(0),
            items="mode_options",
        ),
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="to_schedules", state=Schedules.menu), HOME_BTN),
    getter=user_schedule_getter,
    state=Schedules.my,
)

duties_window = Window(
    Format(
        "{duties_text}\n<tg-spoiler><i>Данные из файла <b>{file_name}</b> от <b>{upload_date}</b>\nМеню обновлено в <b>{current_time_str}</b></i></tg-spoiler>"
    ),
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
    Row(SwitchTo(Const("↩️ Назад"), id="to_schedules", state=Schedules.menu), HOME_BTN),
    getter=duty_schedule_getter,
    state=Schedules.duties,
)

group_window = Window(
    Format(
        "{group_text}\n<tg-spoiler><i>Данные из файла <b>{file_name}</b> от <b>{upload_date}</b>\nМеню обновлено в <b>{current_time_str}</b></i></tg-spoiler>"
    ),
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
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.menu), HOME_BTN),
    getter=group_schedule_getter,
    state=Schedules.group,
)

heads_window = Window(
    Format(
        "{heads_text}\n<tg-spoiler><i>Данные из файла <b>{file_name}</b> от <b>{upload_date}</b>\nМеню обновлено в <b>{current_time_str}</b></i></tg-spoiler>"
    ),
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
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.menu), HOME_BTN),
    getter=head_schedule_getter,
    state=Schedules.heads,
)

tutors_window = Window(
    Format(
        "{tutors_text}\n\n<tg-spoiler><i>Данные из <b><a href='okc.ertelecom.ru/yii/tutor-graph/stp/graph'>Графика наставников</a></b> на <b>{data_created_at}</b>\nМеню обновлено в <b>{current_time_str}</b></i></tg-spoiler>"
    ),
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
            state=Schedules.tutors_calendar,
        ),
    ),
    Row(
        Radio(
            Format("🔘 {item[1]}"),
            Format("⚪️ {item[1]}"),
            id="tutors_schedule_mode",
            item_id_getter=operator.itemgetter(0),
            items="mode_options",
        ),
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.menu), HOME_BTN),
    getter=tutors_schedule_getter,
    state=Schedules.tutors,
)

# Окна календарей
my_schedule_calendar_window = Window(
    Format("<b>👔 Мой график • {month}</b>\n\n· Точками отмечены рабочие дни"),
    ExchangeCalendar(id="my_schedule_calendar"),
    Button(
        Const("📝 Вид текста"),
        id="text_view",
        on_click=switch_to_text_view,
    ),
    Button(Const("🗳 Мои сделки"), id="my_exchanges", on_click=open_my_exchanges),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.my), HOME_BTN),
    getter=my_schedule_calendar_getter,
    state=Schedules.my_calendar,
)

duties_calendar_window = Window(
    Const("<b>📅 Выбор даты для дежурных</b>\n\nВыберите дату из календаря:"),
    RussianCalendar(id="duties_calendar", on_click=on_date_selected),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.duties), HOME_BTN),
    state=Schedules.duties_calendar,
)

group_calendar_window = Window(
    Const("<b>📅 Выбор даты для группы</b>\n\nВыберите дату из календаря:"),
    RussianCalendar(id="group_calendar", on_click=on_date_selected),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.group), HOME_BTN),
    state=Schedules.group_calendar,
)

heads_calendar_window = Window(
    Const("<b>📅 Выбор даты для руководителей</b>\n\nВыберите дату из календаря:"),
    RussianCalendar(id="heads_calendar", on_click=on_date_selected),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.heads), HOME_BTN),
    state=Schedules.heads_calendar,
)

tutors_calendar_window = Window(
    Const("<b>📅 Выбор даты для наставников</b>\n\nВыберите дату из календаря:"),
    RussianCalendar(id="tutors_calendar", on_click=on_date_selected),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Schedules.tutors), HOME_BTN),
    state=Schedules.tutors_calendar,
)


async def on_start(_on_start: Any, dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        dialog_manager: Менеджер диалога
    """
    # Стандартный режим отображения личного графика на "Кратко"
    my_schedule_mode: ManagedRadio = dialog_manager.find("my_schedule_mode")
    await my_schedule_mode.set_checked("compact")

    # Стандартный режим отображения графика наставников на "Только мое"
    tutors_schedule_mode: ManagedRadio = dialog_manager.find("tutors_schedule_mode")
    await tutors_schedule_mode.set_checked("mine")


schedules_dialog = Dialog(
    menu_window,
    my_window,
    group_window,
    duties_window,
    heads_window,
    tutors_window,
    my_schedule_calendar_window,
    duties_calendar_window,
    group_calendar_window,
    heads_calendar_window,
    tutors_calendar_window,
    on_start=on_start,
)

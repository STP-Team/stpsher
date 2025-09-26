from aiogram_dialog.widgets.kbd import (
    Button,
    Row,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.callbacks.common.schedule_functions import (
    do_nothing,
    next_day,
    next_month,
    prev_day,
    prev_month,
    today,
)
from tgbot.dialogs.callbacks.user_functions import (
    switch_to_detailed,
)
from tgbot.dialogs.getters.common.schedule_getters import (
    detailed_schedule_getter,
    duty_schedule_getter,
    head_schedule_getter,
    month_navigation_getter,
)
from tgbot.dialogs.getters.user.user_getters import db_getter
from tgbot.misc.states.user.main import UserSG

schedule_window = Window(
    Format("""<b>📅 Меню графиков</b>

Здесь ты найдешь все, что связано с графиками"""),
    Row(
        SwitchTo(
            Const("👔 Мой график"),
            id="schedule_my",
            state=UserSG.schedule_my,
        ),
        SwitchTo(
            Const("❤️ Моя группа"),
            id="schedule_group",
            state=UserSG.schedule_group,
        ),
    ),
    Row(
        SwitchTo(
            Const("👮‍♂️ Дежурные"),
            id="schedule_duties",
            state=UserSG.schedule_duties,
        ),
        SwitchTo(
            Const("👑 Руководители"),
            id="schedule_heads",
            state=UserSG.schedule_heads,
        ),
    ),
    SwitchTo(Const("↩️ Назад"), id="back_to_menu", state=UserSG.menu),
    getter=db_getter,
    state=UserSG.schedule,
)

schedule_my_window = Window(
    Format("{schedule_text}"),
    Row(
        Button(
            Const("◀️"),
            id="prev_month",
            on_click=prev_month,
        ),
        Button(
            Format("{month_display}"),
            id="current_month",
            on_click=do_nothing,
        ),
        Button(
            Const("▶️"),
            id="next_month",
            on_click=next_month,
        ),
    ),
    Button(
        Const("📋 Подробнее"),
        id="detailed",
        on_click=switch_to_detailed,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="to_schedules", state=UserSG.schedule),
        SwitchTo(Const("🏠 Домой"), id="home", state=UserSG.menu),
    ),
    getter=month_navigation_getter,
    state=UserSG.schedule_my,
)


schedule_duties_window = Window(
    Format("{duties_text}"),
    Row(
        Button(
            Const("◀️"),
            id="prev_day",
            on_click=prev_day,
        ),
        Button(
            Format("📅 {date_display}"),
            id="current_date",
            on_click=do_nothing,
        ),
        Button(
            Const("▶️"),
            id="next_day",
            on_click=next_day,
        ),
    ),
    Button(
        Const("📍 Сегодня"),
        id="today",
        on_click=today,
        when="is_today == False",
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="to_schedules", state=UserSG.schedule),
        SwitchTo(Const("🏠 Домой"), id="home", state=UserSG.menu),
    ),
    getter=duty_schedule_getter,
    state=UserSG.schedule_duties,
)

schedule_group_window = Window(
    Format("""<b>❤️ Моя группа</b>

Здесь будет отображаться расписание вашей группы
<i>Функционал в разработке...</i>"""),
    Row(
        SwitchTo(Const("↩️ Назад"), id="to_schedules", state=UserSG.schedule),
        SwitchTo(Const("🏠 Домой"), id="home", state=UserSG.menu),
    ),
    getter=db_getter,
    state=UserSG.schedule_group,
)

schedule_heads_window = Window(
    Format("{heads_text}"),
    Row(
        Button(
            Const("◀️"),
            id="prev_day",
            on_click=prev_day,
        ),
        Button(
            Format("📅 {date_display}"),
            id="current_date",
            on_click=do_nothing,
        ),
        Button(
            Const("▶️"),
            id="next_day",
            on_click=next_day,
        ),
    ),
    Button(
        Const("📍 Сегодня"),
        id="today",
        on_click=today,
        when="is_today == False",
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="to_schedules", state=UserSG.schedule),
        SwitchTo(Const("🏠 Домой"), id="home", state=UserSG.menu),
    ),
    getter=head_schedule_getter,
    state=UserSG.schedule_heads,
)

schedule_my_detailed_window = Window(
    Format("{schedule_text}"),
    Row(
        Button(
            Const("◀️"),
            id="prev_month",
            on_click=prev_month,
        ),
        Button(
            Format("{month_display}"),
            id="current_month",
            on_click=do_nothing,
        ),
        Button(
            Const("▶️"),
            id="next_month",
            on_click=next_month,
        ),
    ),
    SwitchTo(
        Const("📋 Кратко"),
        id="compact",
        state=UserSG.schedule_my,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="to_schedules", state=UserSG.schedule),
        SwitchTo(Const("🏠 Домой"), id="home", state=UserSG.menu),
    ),
    getter=detailed_schedule_getter,
    state=UserSG.schedule_my_detailed,
)

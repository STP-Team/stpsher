from aiogram_dialog.widgets.kbd import (
    CurrentPage,
    FirstPage,
    LastPage,
    NextPage,
    PrevPage,
    Radio,
    Row,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format, List
from aiogram_dialog.window import Window

from tgbot.dialogs.events.common.filters import on_filter_change
from tgbot.misc.states.dialogs.user import UserSG


def create_achievements_windows(state_group, menu_state, achievements_filter_getter):
    """Create achievements windows for a given state group with role-based filtering"""

    is_user_role = state_group == UserSG
    print(is_user_role)

    # Создаем фильтр для первой категории (позиция или подразделение)
    if is_user_role:
        first_filter = Radio(
            Format("🔘 {item[1]}"),
            Format("⚪️ {item[1]}"),
            id="achievement_position_filter",
            item_id_getter=lambda item: item[0],
            items="position_radio_data",
            on_click=on_filter_change,
        )
    else:
        first_filter = Radio(
            Format("🔘 {item[1]}"),
            Format("⚪️ {item[1]}"),
            id="achievement_division_filter",
            item_id_getter=lambda item: item[0],
            items="division_radio_data",
            on_click=on_filter_change,
        )

    achievements_window = Window(
        Format("""🎯 <b>Достижения</b>

Здесь отображаются все возможные достижения, которые можно получить
"""),
        List(
            Format("""{pos}. <b>{item[1]}</b>
<blockquote>🏅 Награда: {item[2]} баллов
📝 Описание: {item[3]}
🔰 Должность: {item[4]}
🕒 Начисление: {item[5]}</blockquote>\n"""),
            items="achievements",
            id="achievements_list",
            page_size=4,
        ),
        Const("<i>Используй кнопки для выбора страницы или фильтров</i>"),
        Row(
            FirstPage(
                scroll="achievements_list",
                text=Format("1"),
            ),
            PrevPage(
                scroll="achievements_list",
                text=Format("<"),
            ),
            CurrentPage(
                scroll="achievements_list",
                text=Format("{current_page1}"),
            ),
            NextPage(
                scroll="achievements_list",
                text=Format(">"),
            ),
            LastPage(
                scroll="achievements_list",
                text=Format("{target_page1}"),
            ),
        ),
        first_filter,
        Radio(
            Format("🔘 {item[1]}"),
            Format("⚪️ {item[1]}"),
            id="achievement_period_filter",
            item_id_getter=lambda item: item[0],
            items="period_radio_data",
            on_click=on_filter_change,
        ),
        Row(
            SwitchTo(Const("↩️ Назад"), id="menu", state=menu_state),
            SwitchTo(Const("🏠 Домой"), id="home", state=menu_state),
        ),
        getter=achievements_filter_getter,
        state=state_group.game_achievements,
    )

    return (achievements_window,)

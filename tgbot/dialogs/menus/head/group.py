"""Генерация диалога управления группой."""

from typing import Any

from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, ManagedRadio, Radio, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.heads.group import (
    close_group_dialog,
)
from tgbot.dialogs.getters.heads.group.rating import get_rating_display_data
from tgbot.dialogs.states.heads.group import HeadGroupSG

menu_window = Window(
    Const("""❤️ <b>Моя группа</b>
    
<i>Используй меню для выбора действия</i>"""),
    Row(
        SwitchTo(Const("📅 График"), id="schedule", state=HeadGroupSG.schedule),
        SwitchTo(Const("🎖️ Рейтинг"), id="rating", state=HeadGroupSG.rating),
    ),
    Row(
        SwitchTo(Const("👥 Состав"), id="members", state=HeadGroupSG.members),
        SwitchTo(Const("🏮 Игра"), id="game", state=HeadGroupSG.game),
    ),
    Button(Const("↩️ Назад"), id="home", on_click=close_group_dialog),
    state=HeadGroupSG.menu,
)

schedule_window = Window(
    Const("""📅 <b>График</b>"""),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_group_dialog),
    ),
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
        Button(Const("🏠 Домой"), id="home", on_click=close_group_dialog),
    ),
    getter=get_rating_display_data,
    state=HeadGroupSG.rating,
)

members_window = Window(
    Const("""👥 <b>Состав</b>"""),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_group_dialog),
    ),
    state=HeadGroupSG.members,
)

game_window = Window(
    Const("""🏮 <b>Игра</b>"""),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=HeadGroupSG.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_group_dialog),
    ),
    state=HeadGroupSG.game,
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


head_group_dialog = Dialog(
    menu_window,
    schedule_window,
    rating_window,
    members_window,
    game_window,
    on_start=on_start,
)

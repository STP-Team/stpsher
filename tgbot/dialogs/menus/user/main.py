"""Генерация диалога для специалистов."""

from typing import Any

from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import Button, ManagedRadio, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.events.common.game.game import start_game_dialog
from tgbot.dialogs.events.common.groups import start_groups_dialog
from tgbot.dialogs.events.common.search import start_search_dialog
from tgbot.dialogs.getters.common.db import db_getter
from tgbot.dialogs.menus.user.kpi import (
    kpi_requirements_window,
    kpi_salary_window,
    kpi_window,
)
from tgbot.dialogs.menus.user.schedule import (
    schedule_duties_window,
    schedule_group_window,
    schedule_heads_window,
    schedule_my_window,
    schedule_window,
)
from tgbot.dialogs.states.user import UserSG

menu_window = Window(
    Format("""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

<i>Используй меню для взаимодействия с ботом</i>"""),
    Row(
        SwitchTo(Const("📅 Графики"), id="schedules", state=UserSG.schedule),
        SwitchTo(Const("🌟 Показатели"), id="kpi", state=UserSG.kpi),
    ),
    Button(Const("🏮 Игра"), id="game", on_click=start_game_dialog),
    Row(
        Button(
            Const("🕵🏻 Поиск сотрудника"), id="search", on_click=start_search_dialog
        ),
        Button(Const("👯‍♀️ Группы"), id="groups", on_click=start_groups_dialog),
    ),
    state=UserSG.menu,
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


user_dialog = Dialog(
    menu_window,
    schedule_window,
    schedule_my_window,
    schedule_duties_window,
    schedule_group_window,
    schedule_heads_window,
    kpi_window,
    kpi_requirements_window,
    kpi_salary_window,
    on_start=on_start,
    getter=db_getter,
)

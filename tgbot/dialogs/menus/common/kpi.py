"""Генерация диалога для kpi."""

from typing import Any

from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.kpi import close_kpi_dialog
from tgbot.dialogs.getters.common.game.kpi import (
    kpi_getter,
    kpi_requirements_getter,
    salary_getter,
)
from tgbot.dialogs.states.common.kpi import KPI

menu_window = Window(
    Format("{kpi_text}"),
    Row(
        SwitchTo(
            Const("🧮 Нормативы"),
            id="calculator",
            state=KPI.requirements,
        ),
        SwitchTo(
            Const("💰 Зарплата"),
            id="salary",
            state=KPI.salary,
        ),
    ),
    SwitchTo(Const("🔄 Обновить"), id="update", state=KPI.menu),
    Button(Const("↩️ Назад"), id="menu", on_click=close_kpi_dialog),
    getter=kpi_getter,
    state=KPI.menu,
)

requirements_window = Window(
    Format("{requirements_text}"),
    Row(
        SwitchTo(Const("🌟 Показатели"), id="kpi", state=KPI.menu),
        SwitchTo(
            Const("💰 Зарплата"),
            id="salary",
            state=KPI.salary,
        ),
    ),
    SwitchTo(Const("🔄 Обновить"), id="update", state=KPI.requirements),
    Button(Const("↩️ Назад"), id="menu", on_click=close_kpi_dialog),
    getter=kpi_requirements_getter,
    state=KPI.requirements,
)

salary_window = Window(
    Format("{salary_text}"),
    Row(
        SwitchTo(Const("🌟 Показатели"), id="kpi", state=KPI.menu),
        SwitchTo(
            Const("🧮 Нормативы"),
            id="calculator",
            state=KPI.requirements,
        ),
    ),
    SwitchTo(Const("🔄 Обновить"), id="update", state=KPI.salary),
    Button(Const("↩️ Назад"), id="menu", on_click=close_kpi_dialog),
    getter=salary_getter,
    state=KPI.salary,
)


async def on_start(_on_start: Any, _dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        _dialog_manager: Менеджер диалога
    """
    pass


kpi_dialog = Dialog(
    menu_window,
    requirements_window,
    salary_window,
    on_start=on_start,
)

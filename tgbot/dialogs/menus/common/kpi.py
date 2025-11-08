"""Генерация диалога для kpi."""

from typing import Any

from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.getters.common.game.kpi import (
    kpi_getter,
    kpi_requirements_getter,
    salary_getter,
)
from tgbot.dialogs.states.common.kpi import KPI
from tgbot.dialogs.widgets.buttons import HOME_BTN

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
    HOME_BTN,
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
    HOME_BTN,
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
    HOME_BTN,
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

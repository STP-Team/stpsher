"""Генерация окон показателей для руководителей."""

from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.getters.common.kpi import (
    kpi_getter,
    kpi_requirements_getter,
    salary_getter,
)
from tgbot.dialogs.states.head import HeadSG

kpi_window = Window(
    Format("{kpi_text}"),
    Row(
        SwitchTo(
            Const("🧮 Нормативы"),
            id="calculator",
            state=HeadSG.kpi_requirements,
        ),
        SwitchTo(
            Const("💰 Зарплата"),
            id="salary",
            state=HeadSG.salary,
        ),
    ),
    SwitchTo(Const("🔄 Обновить"), id="update", state=HeadSG.kpi),
    SwitchTo(Const("↩️ Назад"), id="menu", state=HeadSG.menu),
    getter=kpi_getter,
    state=HeadSG.kpi,
)

kpi_requirements_window = Window(
    Format("{requirements_text}"),
    Row(
        SwitchTo(Const("🌟 Показатели"), id="kpi", state=HeadSG.kpi),
        SwitchTo(
            Const("💰 Зарплата"),
            id="salary",
            state=HeadSG.salary,
        ),
    ),
    SwitchTo(Const("🔄 Обновить"), id="update", state=HeadSG.kpi_requirements),
    SwitchTo(Const("↩️ Назад"), id="menu", state=HeadSG.menu),
    getter=kpi_requirements_getter,
    state=HeadSG.kpi_requirements,
)

salary_window = Window(
    Format("{salary_text}"),
    Row(
        SwitchTo(Const("🌟 Показатели"), id="kpi", state=HeadSG.kpi),
        SwitchTo(
            Const("🧮 Нормативы"),
            id="calculator",
            state=HeadSG.kpi_requirements,
        ),
    ),
    SwitchTo(Const("🔄 Обновить"), id="update", state=HeadSG.salary),
    SwitchTo(Const("↩️ Назад"), id="menu", state=HeadSG.menu),
    getter=salary_getter,
    state=HeadSG.salary,
)

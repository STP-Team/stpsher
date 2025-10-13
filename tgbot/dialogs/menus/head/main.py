"""Генерация диалога для руководителей."""

import logging
from typing import Any

from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.events.common.game.game import start_game_dialog
from tgbot.dialogs.events.common.groups import start_groups_dialog
from tgbot.dialogs.events.common.kpi import start_kpi_dialog
from tgbot.dialogs.events.common.schedules import start_schedules_dialog
from tgbot.dialogs.events.common.search import start_search_dialog
from tgbot.dialogs.events.heads.group import start_group_dialog
from tgbot.dialogs.getters.common.db import db_getter
from tgbot.dialogs.menus.widgets import SUPPORT_BTN
from tgbot.dialogs.states.heads.head import HeadSG

logger = logging.getLogger(__name__)


menu_window = Window(
    Format("""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

<i>Используй меню для взаимодействия с ботом</i>"""),
    Row(
        Button(Const("📅 Графики"), id="schedules", on_click=start_schedules_dialog),
        Button(Const("🌟 Показатели"), id="kpi", on_click=start_kpi_dialog),
    ),
    Button(Const("🏮 Игра"), id="game", on_click=start_game_dialog),
    Button(Const("❤️ Моя группа"), id="my_group", on_click=start_group_dialog),
    Row(
        Button(
            Const("🕵🏻 Поиск сотрудника"), id="search", on_click=start_search_dialog
        ),
        Button(Const("👯‍♀️ Группы"), id="groups", on_click=start_groups_dialog),
    ),
    SUPPORT_BTN,
    state=HeadSG.menu,
)


async def on_start(_on_start: Any, _dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        _dialog_manager: Менеджер диалога
    """
    pass


head_dialog = Dialog(
    menu_window,
    on_start=on_start,
    getter=db_getter,
)

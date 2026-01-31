"""Генерация диалога для руководителей."""

import logging
from typing import Any

from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.events.heads.group import start_group_dialog
from tgbot.dialogs.states.head import HeadSG
from tgbot.dialogs.widgets.buttons import (
    GAME_BTN,
    GROUPS_BTN,
    KPI_BTN,
    SCHEDULES_BTN,
    SEARCH_BTN,
    SUPPORT_BTN,
)

logger = logging.getLogger(__name__)


menu_window = Window(
    Format("""👋 <b>Привет</b>!

Я - бот-помощник СТП

<i>Используй меню для взаимодействия с ботом</i>"""),
    Row(
        SCHEDULES_BTN,
        KPI_BTN,
    ),
    GAME_BTN,
    Button(Const("❤️ Моя группа"), id="my_group", on_click=start_group_dialog),
    Row(SEARCH_BTN, GROUPS_BTN),
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


head_dialog = Dialog(menu_window, on_start=on_start)

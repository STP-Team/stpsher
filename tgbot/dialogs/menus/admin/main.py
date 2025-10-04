"""Генерация диалога для администраторов."""

from typing import Any

from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.events.common.broadcast import start_broadcast_dialog
from tgbot.dialogs.events.common.groups import start_groups_dialog
from tgbot.dialogs.events.common.search import start_search_dialog
from tgbot.dialogs.getters.common.db import db_getter
from tgbot.dialogs.states.admin import AdminSG

menu_window = Window(
    Format("""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

<i>Используй меню для взаимодействия с ботом</i>"""),
    Button(Const("📢 Рассылки"), id="broadcast", on_click=start_broadcast_dialog),
    Row(
        Button(
            Const("🕵🏻 Поиск сотрудника"), id="search", on_click=start_search_dialog
        ),
        Button(Const("👯‍♀️ Группы"), id="groups", on_click=start_groups_dialog),
    ),
    state=AdminSG.menu,
)


async def on_start(_on_start: Any, _dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        _dialog_manager: Менеджер диалога
    """
    pass


admin_dialog = Dialog(
    menu_window,
    on_start=on_start,
    getter=db_getter,
)

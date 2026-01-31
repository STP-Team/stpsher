"""Генерация диалога для администраторов."""

from typing import Any

from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.events.common.broadcast import start_broadcast_dialog
from tgbot.dialogs.events.common.files.files import start_files_dialog
from tgbot.dialogs.states.admin import AdminSG
from tgbot.dialogs.widgets.buttons import GROUPS_BTN, SEARCH_BTN, SUPPORT_BTN

menu_window = Window(
    Format("""👋 <b>Привет</b>!

Я - бот-помощник СТП

<i>Используй меню для взаимодействия с ботом</i>"""),
    Row(
        Button(Const("📂 Файлы"), id="files", on_click=start_files_dialog),
        Button(Const("📢 Рассылки"), id="broadcast", on_click=start_broadcast_dialog),
    ),
    Row(SEARCH_BTN, GROUPS_BTN),
    SUPPORT_BTN,
    state=AdminSG.menu,
)


async def on_start(_on_start: Any, _dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        _dialog_manager: Менеджер диалога
    """
    pass


admin_dialog = Dialog(menu_window, on_start=on_start)

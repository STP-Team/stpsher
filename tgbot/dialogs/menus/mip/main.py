"""Генерация диалога для МИП."""

from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.events.common.broadcast import start_broadcast_dialog
from tgbot.dialogs.events.common.files.files import start_files_dialog
from tgbot.dialogs.events.common.game.game import start_game_dialog
from tgbot.dialogs.events.common.search import start_search_dialog
from tgbot.dialogs.states.mip import MipSG
from tgbot.dialogs.widgets.buttons import SUPPORT_BTN

menu_window = Window(
    Format("""👋 <b>Привет</b>!

Я - бот-помощник СТП

<i>Используй меню для взаимодействия с ботом</i>"""),
    Row(
        Button(Const("📂 Файлы"), id="files", on_click=start_files_dialog),
        Button(Const("📢 Рассылки"), id="broadcast", on_click=start_broadcast_dialog),
    ),
    Button(Const("🏮 Игра"), id="game", on_click=start_game_dialog),
    Row(
        Button(
            Const("🕵🏻 Поиск сотрудника"), id="search", on_click=start_search_dialog
        ),
        # Button(Const("👯‍♀️ Группы"), id="groups", on_click=start_groups_dialog),
    ),
    SUPPORT_BTN,
    state=MipSG.menu,
)


async def on_start(_on_start, _dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        _dialog_manager: Менеджер диалога
    """
    pass


mip_dialog = Dialog(menu_window)

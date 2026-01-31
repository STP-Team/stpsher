"""Генерация диалога для ГОК."""

from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import Row
from aiogram_dialog.widgets.text import Format
from aiogram_dialog.window import Window

from tgbot.dialogs.states.gok import GokSG
from tgbot.dialogs.widgets.buttons import GAME_BTN, GROUPS_BTN, SEARCH_BTN, SUPPORT_BTN

menu_window = Window(
    Format("""👋 <b>Привет</b>!

Я - бот-помощник СТП

<i>Используй меню для взаимодействия с ботом</i>"""),
    GAME_BTN,
    Row(SEARCH_BTN, GROUPS_BTN),
    SUPPORT_BTN,
    state=GokSG.menu,
)


async def on_start(_on_start, _dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        _dialog_manager: Менеджер диалога
    """
    pass


gok_dialog = Dialog(menu_window, on_start=on_start)

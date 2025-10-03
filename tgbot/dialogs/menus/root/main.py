"""Генерация диалога для root."""

from typing import Any

from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import ManagedRadio, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.getters.common.db import db_getter
from tgbot.dialogs.menus.root.search import (
    search_heads_window,
    search_no_results_window,
    search_query_window,
    search_results_window,
    search_specialists_window,
    search_user_info_window,
    search_window,
)
from tgbot.misc.states.dialogs.root import RootSG

menu_window = Window(
    Format("""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

<i>Используй меню для взаимодействия с ботом</i>"""),
    Row(
        SwitchTo(Const("🕵🏻 Поиск сотрудника"), id="search", state=RootSG.search),
        SwitchTo(Const("👯‍♀️ Группы"), id="groups", state=RootSG.groups),
    ),
    state=RootSG.menu,
)


async def on_start(_on_start: Any, dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        dialog_manager: Менеджер диалога
    """
    # Фильтр поиска по направлению на "Все"
    search_divisions: ManagedRadio = dialog_manager.find("search_divisions")
    await search_divisions.set_checked("all")

    # Фильтр групповых команд на "Пользователь"
    groups_cmds_filter: ManagedRadio = dialog_manager.find("groups_cmds_filter")
    await groups_cmds_filter.set_checked("user")


root_dialog = Dialog(
    menu_window,
    search_window,
    search_specialists_window,
    search_heads_window,
    search_query_window,
    search_results_window,
    search_no_results_window,
    search_user_info_window,
    on_start=on_start,
    getter=db_getter,
)

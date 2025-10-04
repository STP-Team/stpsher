"""Генерация диалога для МИП."""

from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import Button, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.events.common.broadcast import start_broadcast_dialog
from tgbot.dialogs.events.common.groups import start_groups_dialog
from tgbot.dialogs.getters.common.db import db_getter
from tgbot.dialogs.menus.mip.game.achievements import game_achievements_window
from tgbot.dialogs.menus.mip.game.activations import (
    game_activation_detail_window,
    game_activations_empty_window,
    game_activations_window,
)
from tgbot.dialogs.menus.mip.game.game import game_window
from tgbot.dialogs.menus.mip.game.products import game_products_window
from tgbot.dialogs.menus.mip.search import (
    search_heads_window,
    search_no_results_window,
    search_query_window,
    search_results_window,
    search_specialists_window,
    search_user_info_window,
    search_window,
)
from tgbot.dialogs.states.mip import MipSG

menu_window = Window(
    Format("""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

Здесь ты можешь:
• Просматривать список достижений
• Просматривать список предметов
• Активировать покупки специалистов

<i>Используй меню для взаимодействия с ботом</i>"""),
    Row(
        Button(Const("📅 Графики"), id="schedules"),
        Button(Const("📢 Рассылки"), id="broadcast", on_click=start_broadcast_dialog),
    ),
    SwitchTo(Const("🏮 Игра"), id="game", state=MipSG.game),
    Row(
        SwitchTo(Const("🕵🏻 Поиск сотрудника"), id="search", state=MipSG.search),
        Button(Const("👯‍♀️ Группы"), id="groups", on_click=start_groups_dialog),
    ),
    state=MipSG.menu,
)


async def on_start(_on_start, dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        dialog_manager: Менеджер диалога
    """
    # Фильтр поиска по направлению на "Все"
    # search_divisions: ManagedRadio = dialog_manager.find("search_divisions")
    # await search_divisions.set_checked("all")

    # Фильтр групповых команд на "Пользователь"
    # groups_cmds_filter: ManagedRadio = dialog_manager.find("groups_cmds_filter")
    # await groups_cmds_filter.set_checked("user")


mip_dialog = Dialog(
    menu_window,
    game_window,
    game_achievements_window,
    game_products_window,
    game_activations_window,
    game_activation_detail_window,
    game_activations_empty_window,
    search_window,
    search_specialists_window,
    search_heads_window,
    search_query_window,
    search_results_window,
    search_no_results_window,
    search_user_info_window,
    getter=db_getter,
)

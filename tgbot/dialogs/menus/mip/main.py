from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import ManagedRadio, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.getters.user.user_getters import db_getter
from tgbot.dialogs.menus.mip.game.activations import (
    game_activation_detail_window,
    game_activations_empty_window,
    game_activations_window,
)
from tgbot.dialogs.menus.mip.game.game import game_window
from tgbot.dialogs.menus.mip.search import (
    search_heads_window,
    search_no_results_window,
    search_query_window,
    search_results_window,
    search_specialists_window,
    search_user_info_window,
    search_window,
)
from tgbot.misc.states.dialogs.mip import MipSG

menu_window = Window(
    Format("""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

Здесь ты можешь:
• Просматривать список достижений
• Просматривать список предметов
• Активировать покупки специалистов

<i>Используй меню для взаимодействия с ботом</i>"""),
    SwitchTo(Const("🏮 Игра"), id="game", state=MipSG.game),
    Row(
        SwitchTo(Const("🕵🏻 Поиск сотрудника"), id="search", state=MipSG.search),
        SwitchTo(Const("👯‍♀️ Группы"), id="groups", state=MipSG.groups),
    ),
    getter=db_getter,
    state=MipSG.menu,
)


async def on_start(start_data, dialog_manager: DialogManager, **kwargs):
    """Установка значений по умолчанию при запуске диалога"""
    search_divisions: ManagedRadio = dialog_manager.find("search_divisions")
    await search_divisions.set_checked("all")


mip_dialog = Dialog(
    menu_window,
    game_window,
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
    on_start=on_start,
    getter=db_getter,
)

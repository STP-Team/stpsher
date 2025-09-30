from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import ManagedRadio, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.getters.user.user_getters import db_getter
from tgbot.dialogs.menus.gok.search import (
    search_heads_window,
    search_no_results_window,
    search_query_window,
    search_results_window,
    search_specialists_window,
    search_user_info_window,
    search_window,
)
from tgbot.misc.states.dialogs.gok import GokSG

menu_window = Window(
    Format("""👋 Привет, <b>{user.fullname}</b>!

Я - бот-помощник СТП

Здесь ты можешь:
• Просматривать список достижений
• Просматривать список предметов
• Активировать покупки специалистов

<i>Используй меню для взаимодействия с ботом</i>"""),
    SwitchTo(
        Const("✍️ Активация предметов"),
        id="products_activation",
        state=GokSG.products_activation,
    ),
    Row(
        SwitchTo(Const("🎯 Достижения"), id="achievements", state=GokSG.groups),
        SwitchTo(Const("👏 Предметы"), id="products", state=GokSG.groups),
    ),
    Row(
        SwitchTo(Const("🕵🏻 Поиск сотрудника"), id="search", state=GokSG.search),
        SwitchTo(Const("👯‍♀️ Группы"), id="groups", state=GokSG.groups),
    ),
    getter=db_getter,
    state=GokSG.menu,
)


async def on_start(start_data, dialog_manager: DialogManager, **kwargs):
    """Установка значений по умолчанию при запуске диалога"""
    search_divisions: ManagedRadio = dialog_manager.find("search_divisions")
    await search_divisions.set_checked("all")


gok_dialog = Dialog(
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

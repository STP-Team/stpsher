"""Генерация диалога для специалистов."""

from typing import Any

from aiogram import F
from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import Back, Button, Row, SwitchTo, Url
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.events.common.game.game import start_game_dialog
from tgbot.dialogs.events.common.kpi import start_kpi_dialog
from tgbot.dialogs.events.common.schedules import start_schedules_dialog
from tgbot.dialogs.events.common.search import start_search_dialog
from tgbot.dialogs.getters.common.db import db_getter
from tgbot.dialogs.states.user import UserSG

menu_window = Window(
    Format("""👋 <b>Привет</b>!

Я - бот-помощник СТП

<i>Используй меню для взаимодействия с ботом</i>"""),
    Row(
        Button(Const("📅 Графики"), id="schedules", on_click=start_schedules_dialog),
        Button(Const("🌟 Показатели"), id="kpi", on_click=start_kpi_dialog),
    ),
    Row(
        Button(Const("🏮 Игра"), id="game", on_click=start_game_dialog),
        SwitchTo(
            Const("📣 Рупор"),
            id="horn",
            state=UserSG.horn,
            when=F["user"].division == "НЦК",  # type: ignore[arg-type]
        ),
    ),
    Row(
        Button(
            Const("🕵🏻 Поиск сотрудника"), id="search", on_click=start_search_dialog
        ),
        # Button(Const("👯‍♀️ Группы"), id="groups", on_click=start_groups_dialog),
    ),
    # SUPPORT_BTN,
    getter=db_getter,
    state=UserSG.menu,
)


horn_window = Window(
    Const("📣 <b>Рупор</b>\n"),
    Const("""Возник вопрос по процессу работы? Не нужно гадать, кого спросить!
По всем непонятным процессам, правилам, инструментам и идеям есть один пункт назначения – <b>Рупор</b>

<blockquote>Рупор – это площадка, где ты можешь анонимно или открыто задать вопрос по работе, предложить идею по развитию отдела/компании

Кроме того, если твоя идея поможет развитию отдела или компании – ты можешь получить дополнительную прибавку к премии</blockquote>"""),
    Row(
        Url(Const("💡 Задать вопрос"), url=Const("forms.gle/krFwo1Q16sTStMxHA")),
        Back(Const("↩️ Назад"), id="back"),
    ),
    state=UserSG.horn,
)


async def on_start(_on_start: Any, _dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        _dialog_manager: Менеджер диалога
    """


user_dialog = Dialog(menu_window, horn_window, on_start=on_start)

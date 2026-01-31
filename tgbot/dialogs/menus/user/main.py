"""Генерация диалога для специалистов."""

from typing import Any

from aiogram import F
from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import (
    CurrentPage,
    FirstPage,
    LastPage,
    NextPage,
    PrevPage,
    Row,
    SwitchTo,
    Url,
)
from aiogram_dialog.widgets.text import Const, Format, List
from aiogram_dialog.window import Window

from tgbot.dialogs.getters.common.db import db_getter
from tgbot.dialogs.getters.user.main import horn_getter, tests_getter
from tgbot.dialogs.states.user import UserSG
from tgbot.dialogs.widgets.buttons import (
    GAME_BTN,
    GROUPS_BTN,
    HOME_BTN,
    KPI_BTN,
    SCHEDULES_BTN,
    SEARCH_BTN,
    SUPPORT_BTN,
)

menu_window = Window(
    Format(
        """{hi} <b>Привет</b>!

Я - бот-помощник СТП

<i>Используй меню для взаимодействия с ботом</i>""",
    ),
    Row(
        SCHEDULES_BTN,
        KPI_BTN,
    ),
    Row(
        GAME_BTN,
        SwitchTo(
            Const("📣 Рупор"),
            id="horn",
            state=UserSG.horn,
            when=F["user"].division == "НЦК",  # type: ignore[arg-type]
        ),
    ),
    SwitchTo(
        Const("🧪 Непройденные тесты"),
        id="tests",
        state=UserSG.tests,
        when="have_tests",
    ),
    Row(SEARCH_BTN, GROUPS_BTN),
    SUPPORT_BTN,
    getter=db_getter,
    state=UserSG.menu,
)


horn_window = Window(
    Format("{megaphone} <b>Рупор</b>\n"),
    Const("""Возник вопрос по процессу работы? Не нужно гадать, кого спросить!
По всем непонятным процессам, правилам, инструментам и идеям есть один пункт назначения – <b>Рупор</b>

<blockquote>Рупор – это площадка, где ты можешь анонимно или открыто задать вопрос по работе, предложить идею по развитию отдела/компании

Кроме того, если твоя идея поможет развитию отдела или компании – ты можешь получить дополнительную прибавку к премии</blockquote>"""),
    Row(
        Url(Const("💡 Задать вопрос"), url=Const("forms.gle/krFwo1Q16sTStMxHA")),
    ),
    HOME_BTN,
    getter=horn_getter,
    state=UserSG.horn,
)

tests_window = Window(
    Const("🧪 <b>Непройденные тесты</b>\n"),
    List(
        Format("""{pos}. <b><a href='okc.ertelecom.ru/yii/testing/lk/test?id={item.test_id}'>{item.test_name}</a></b>
<b>Назначен:</b> {item.active_from}
<b>Создатель:</b> {item.creator_fullname}\n"""),
        items="tests",
        id="tests_list",
        page_size=6,
    ),
    Row(
        FirstPage(
            scroll="tests_list",
            text=Format("1"),
        ),
        PrevPage(
            scroll="tests_list",
            text=Format("<"),
        ),
        CurrentPage(
            scroll="tests_list",
            text=Format("{current_page1}"),
        ),
        NextPage(
            scroll="tests_list",
            text=Format(">"),
        ),
        LastPage(
            scroll="tests_list",
            text=Format("{target_page1}"),
        ),
        when=F["tests_length"] > 6,
    ),
    Format(
        "<i>Данные из <b><a href='okc.ertelecom.ru/yii/testing/lk/profile'>Тестов</a></b> на <b>{created_at_str}</b>\nМеню обновлено в <b>{current_time_str}</b></i>"
    ),
    HOME_BTN,
    getter=tests_getter,
    state=UserSG.tests,
)


async def on_start(_on_start: Any, _dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        _dialog_manager: Менеджер диалога
    """


user_dialog = Dialog(
    menu_window,
    horn_window,
    tests_window,
    on_start=on_start,
)

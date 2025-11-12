"""Генерация общих функций для управления группами."""

import operator
from typing import Any

from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import (
    Checkbox,
    Group,
    ManagedRadio,
    Radio,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
    Url,
)
from aiogram_dialog.widgets.text import Const, Format
from magic_filter import F

from tgbot.dialogs.events.common.groups import (
    on_group_selected,
    on_is_casino_allowed_click,
    on_new_user_notify_click,
)
from tgbot.dialogs.getters.common.groups import (
    groups_details_getter,
    groups_getter,
    groups_list_getter,
)
from tgbot.dialogs.menus.common.groups.settings import (
    groups_access_window,
    groups_remove_bot_window,
    groups_service_messages_window,
)
from tgbot.dialogs.states.common.groups import Groups
from tgbot.dialogs.widgets.buttons import HOME_BTN

groups_window = Window(
    Const("""👯‍♀️ <b>Группы</b>

Ты можешь использовать меня для менеджмента групп

<blockquote expandable>🪄 <b>Я умею</b>
∙ Приветствовать новых пользователей
∙ Удалять уволенных
∙ Разрешать доступ к группе конкретных должностям
∙ Удалять сервисные сообщения
∙ Управлять доступом к казино в группе
∙ Просматривать список участников</blockquote>"""),
    Url(
        Const("💌 Пригласить бота"),
        id="joinchat_deeplink",
        url=Format("{joinchat_deeplink}"),
    ),
    Row(
        SwitchTo(
            Const("🛡️ Управление"),
            id="manage",
            state=Groups.list,
        ),
        SwitchTo(Const("💡 Команды"), id="groups_cmds", state=Groups.cmds),
    ),
    HOME_BTN,
    getter=groups_getter,
    state=Groups.menu,
)

groups_cmds_window = Window(
    Const("💡 <b>Команды для групп</b>\n"),
    Const(
        text="""🙋🏻‍♂️ <b>Команды для пользователей в группах</b>

<b>ℹ️ Информация о группе:</b>
∙ <code>/admins</code> - список администраторов группы

<b>💰 Баланс и рейтинг:</b>
∙ <code>/balance</code> - посмотреть свой баланс баллов
∙ <code>/top</code> - рейтинг участников группы по баллам

<b>🎰 Игры казино:</b>
∙ <code>/slots [сумма]</code> - игра в слоты (пример: /slots 50)
∙ <code>/dice [сумма]</code> - игра в кости (пример: /dice 100)
∙ <code>/darts [сумма]</code> - игра в дартс (пример: /darts 25)
∙ <code>/bowling [сумма]</code> - игра в боулинг (пример: /bowling 75)

<b>💡 Примечания:</b>
∙ Минимальная ставка для игр - 10 баллов
∙ Команды /balance и казино доступны только специалистам и дежурным
∙ Казино может быть отключено администратором группы""",
        when="is_user",
    ),
    Const(
        text="""🛡️ <b>Команды для администраторов групп</b>

<b>📌 Управление сообщениями:</b>
∙ <code>/pin</code> - закрепить сообщение (в ответ на сообщение)
∙ <code>/unpin</code> - открепить сообщение (в ответ на закрепленное сообщение)

<b>👥 Управление пользователями:</b>
∙ <code>/mute [время]</code> - замутить пользователя
∙ <code>/unmute</code> - размутить пользователя
∙ <code>/ban</code> - забанить пользователя
∙ <code>/unban</code> - разбанить пользователя

<b>⚙️ Настройки группы:</b>
∙ <code>/settings</code> - настройки группы

<b>📝 Примеры времени для мута:</b>
∙ <code>/mute 30m</code> или <code>/mute 30м</code> - на 30 минут
∙ <code>/mute 2h</code> или <code>/mute 2ч</code> - на 2 часа
∙ <code>/mute 7d</code> или <code>/mute 7д</code> - на 7 дней
∙ <code>/mute</code> - навсегда""",
        when=~F["is_user"],
    ),
    Radio(
        Format("🔘 {item[1]}"),
        Format("⚪️ {item[1]}"),
        id="groups_cmds_filter",
        item_id_getter=operator.itemgetter(0),
        items=[("user", "Пользователь"), ("admin", "Администратор")],
    ),
    Row(SwitchTo(Const("↩️ Назад"), id="back", state=Groups.menu), HOME_BTN),
    state=Groups.cmds,
)

groups_list_window = Window(
    Format(
        """🛡️ <b>Управление группами</b>

Найдено групп: <b>{groups_count}</b>

<i>Выбери группу для просмотра настроек</i>""",
        when="has_groups",
    ),
    Format(
        """🛡️ <b>Управление группами</b>

Чтобы управлять настройками бота в группах, тебе необходимо:
1. Вступить в группу, где добавлен бот
2. Чтобы изменять настройки - получить права администратора

<i>После добавления в группу, вернись в это меню</i>""",
        when=~F["has_groups"],
    ),
    ScrollingGroup(
        Select(
            Format("{item[0]}"),
            id="groups_select",
            item_id_getter=operator.itemgetter(1),
            items="groups",
            on_click=on_group_selected,
        ),
        id="groups_scroll",
        width=2,
        height=6,
        when="has_groups",
        hide_on_single_page=True,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Groups.menu),
        HOME_BTN,
    ),
    getter=groups_list_getter,
    state=Groups.list,
)


groups_list_detail_window = Window(
    Format("""⚙️ <b>Настройки {group_type}</b>: {group_name}
    
<b>Обозначения</b>
- 🟢 Опция включена
- 🔴 Опция выключена

Идентификатор {group_type}: <code>{group_id}</code>"""),
    SwitchTo(
        Const("🛡️ Уровень доступа"),
        id="access_level",
        state=Groups.settings_access,
    ),
    Group(
        Row(
            Checkbox(
                Const("🟢 Приветствие"),
                Const("🔴 Приветствие"),
                id="new_user_notify",
                on_click=on_new_user_notify_click,
            ),
            Checkbox(
                Const("🟢 Казино"),
                Const("🔴 Казино"),
                id="is_casino_allowed",
                on_click=on_is_casino_allowed_click,
            ),
        ),
        Row(
            SwitchTo(
                Const("🗑️ Сервисные сообщения"),
                id="service_messages",
                state=Groups.settings_services,
            ),
        ),
        when=~F["is_channel"],
    ),
    SwitchTo(Const("♻️ Удалить бота"), id="remove_bot", state=Groups.settings_remove),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back_to_list", state=Groups.list),
        HOME_BTN,
    ),
    state=Groups.group_details,
    getter=groups_details_getter,
)


async def on_start(_on_start: Any, dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        dialog_manager: Менеджер диалога
    """
    # Фильтр групповых команд на "Пользователь"
    groups_cmds_filter: ManagedRadio = dialog_manager.find("groups_cmds_filter")
    await groups_cmds_filter.set_checked("user")


groups_dialog = Dialog(
    groups_window,
    groups_list_window,
    groups_list_detail_window,
    groups_cmds_window,
    groups_access_window,
    groups_service_messages_window,
    groups_remove_bot_window,
    on_start=on_start,
)

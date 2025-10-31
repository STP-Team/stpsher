"""Генерация диалога настроек группы."""

import operator

from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import (
    Button,
    Checkbox,
    Group,
    Multiselect,
    Row,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from tgbot.dialogs.events.common.groups import (
    on_confirm_delete_group,
    on_only_employees_click,
    on_role_selected,
    on_service_message_selected,
)
from tgbot.dialogs.getters.common.groups import (
    group_details_access_getter,
    group_details_services_getter,
    group_remove_getter,
)
from tgbot.dialogs.states.common.groups import Groups
from tgbot.dialogs.widgets.buttons import HOME_BTN

groups_access_window = Window(
    Format(
        """🛡️ <b>Уровень доступа к группе</b>: {group_name}

Выбери роли, которые могут вступать в группу
Если не выбрана ни одна роль, доступ открыт для всех"""
    ),
    Checkbox(
        Const("✓ 👔 Только сотрудники 👔"),
        Const("👔 Только сотрудники 👔"),
        id="only_employees",
        on_click=on_only_employees_click,
    ),
    Group(
        Multiselect(
            Format("✓ {item[1]}"),
            Format("{item[1]}"),
            id="access_level_select",
            item_id_getter=operator.itemgetter(0),
            items="roles",
            on_state_changed=on_role_selected,
        ),
        width=2,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Groups.group_details),
        HOME_BTN,
    ),
    state=Groups.settings_access,
    getter=group_details_access_getter,
)

# Окно настройки сервисных сообщений группы
groups_service_messages_window = Window(
    Const(
        """🗑️ <b>Управление сервисными сообщениями</b>

<blockquote expandable><b>Типы сервисных сообщений:</b>
• <b>Вход</b> - "X присоединился к чату"
• <b>Выход</b> - "X покинул чат"
• <b>Прочее</b> - бусты, платежи, уведомления
• <b>Фото</b> - смена фото чата
• <b>Закреп</b> - "X закрепил сообщение"
• <b>Название</b> - смена названия чата
• <b>Видеозвонки</b> - действия с видеозвонками</blockquote>

<i>Выбери типы сообщений для удаления</i>"""
    ),
    Group(
        Multiselect(
            Format("✓ {item[1]}"),
            Format("{item[1]}"),
            id="service_messages_select",
            item_id_getter=operator.itemgetter(0),
            items="service_messages",
            on_state_changed=on_service_message_selected,
        ),
        width=2,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back_to_list", state=Groups.group_details),
        HOME_BTN,
    ),
    state=Groups.settings_services,
    getter=group_details_services_getter,
)

# Окно подтверждения удаления бота из группы
groups_remove_bot_window = Window(
    Format("""⚠️ <b>Подтверждение удаления бота</b>

Группа: <b>{group_name}</b>

<b>Что произойдет:</b>
∙ Бот покинет группу
∙ Группа будет удалена из базы
∙ Все участники будут исключены из состава группы

<b>Это действие необратимо!</b>"""),
    Button(
        Const("🗑️ Подтвердить удаление"),
        id="confirm_delete",
        on_click=on_confirm_delete_group,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Groups.group_details),
        HOME_BTN,
    ),
    state=Groups.settings_remove,
    getter=group_remove_getter,
)

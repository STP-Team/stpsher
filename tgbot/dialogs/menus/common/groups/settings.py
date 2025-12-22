"""Генерация диалога настроек группы."""

import operator

from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import (
    Button,
    Checkbox,
    Group,
    Multiselect,
    Radio,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format
from magic_filter import F

from tgbot.dialogs.events.common.groups import (
    on_ban_member,
    on_confirm_delete_group,
    on_division_selected,
    on_kick_all_inappropriate_users,
    on_kick_inappropriate_user,
    on_kick_member,
    on_member_selected,
    on_only_employees_click,
    on_position_selected,
    on_role_filter_changed,
    on_role_selected,
    on_service_message_selected,
)
from tgbot.dialogs.getters.common.groups import (
    group_details_services_getter,
    group_remove_getter,
    groups_access_getter,
    groups_access_roles_getter,
    groups_members_getter,
    inappropriate_users_getter,
    member_details_getter,
    settings_access_divisions_getter,
    settings_access_positions_getter,
)
from tgbot.dialogs.states.common.groups import Groups
from tgbot.dialogs.widgets.buttons import HOME_BTN

groups_access_window = Window(
    Format(
        """🔓 <b>{group_name}: Доступ</b>

Доступ по должности доступен только после выбора допустимых направлений

<i>Если не выбрана ни одна опция - доступ открыт для всех</i>"""
    ),
    SwitchTo(
        Const("👥 Список участников"),
        id="view_members",
        state=Groups.settings_members,
    ),
    Checkbox(
        Const("✓ 👔 Только сотрудники 👔"),
        Const("👔 Только сотрудники 👔"),
        id="only_employees",
        on_click=on_only_employees_click,
    ),
    Row(
        SwitchTo(
            Const("🛡️ По уровню"),
            id="group_role_access",
            state=Groups.settings_access_roles,
        ),
        SwitchTo(
            Const("🔰 По направлению"),
            id="group_division_access",
            state=Groups.settings_access_divisions,
        ),
    ),
    SwitchTo(
        Const("💼 По должности"),
        id="group_position_access",
        state=Groups.settings_access_positions,
        when="has_allowed_divisions",
    ),
    SwitchTo(
        Const("⚠️ Неподходящие пользователи"),
        id="inappropriate_users",
        state=Groups.inappropriate_users,
        when="has_inappropriate_users",
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Groups.group_details),
        HOME_BTN,
    ),
    getter=groups_access_getter,
    state=Groups.settings_access,
)

groups_access_roles_window = Window(
    Format(
        """🛡️ <b>{group_name}: Доступ по уровню</b>

Выбери роли, которые могут вступать в группу
Если не выбрана ни одна роль, доступ открыт для всех"""
    ),
    Group(
        Multiselect(
            Format("✓ {item[1]}"),
            Format("{item[1]}"),
            id="access_role_select",
            item_id_getter=operator.itemgetter(0),
            items="roles",
            on_state_changed=on_role_selected,
        ),
        width=2,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Groups.settings_access),
        HOME_BTN,
    ),
    getter=groups_access_roles_getter,
    state=Groups.settings_access_roles,
)

settings_access_divisions_window = Window(
    Format(
        """🔰 <b>{group_name}: Доступ по направлению</b>

Выбери направления, которые могут вступать в группу
Если не выбрано ни одно направление, доступ открыт для всех"""
    ),
    Group(
        Multiselect(
            Format("✓ {item[1]}"),
            Format("{item[1]}"),
            id="access_division_select",
            item_id_getter=operator.itemgetter(0),
            items="divisions",
            on_state_changed=on_division_selected,
        ),
        width=2,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Groups.settings_access),
        HOME_BTN,
    ),
    getter=settings_access_divisions_getter,
    state=Groups.settings_access_divisions,
)

settings_access_positions_window = Window(
    Format(
        """🔰 <b>{group_name}: Доступ по должности</b>

Выбери должности, которые могут вступать в группу
Если не выбрана ни одна должность, доступ открыт для всех"""
    ),
    Group(
        Multiselect(
            Format("✓ {item[1]}"),
            Format("{item[1]}"),
            id="access_position_select",
            item_id_getter=operator.itemgetter(0),
            items="positions",
            on_state_changed=on_position_selected,
        ),
        width=1,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Groups.settings_access),
        HOME_BTN,
    ),
    getter=settings_access_positions_getter,
    state=Groups.settings_access_positions,
)

# Окно настройки сервисных сообщений группы
groups_service_messages_window = Window(
    Const(
        """🗑️ <b>{group_name}: Сервисные сообщения</b>

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
    Format("""⚠️ <b>{group_name}: Удаление бота</b>

Группа: <b>{group_name}</b>

<b>Что произойдет:</b>
∙ Бот покинет группу
∙ Группа будет удалена из базы
∙ Бот забудет всех участников группы

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

# Окно списка неподходящих пользователей
inappropriate_users_window = Window(
    Format(
        """⚠️ <b>{group_name}: Неподходящие пользователи</b>

Найдено {users_count} пользователей, которые не соответствуют настройкам группы

<i>Нажми на пользователя, чтобы исключить его из группы</i>""",
        when="has_inappropriate_users",
    ),
    Format(
        """⚠️ <b>{group_name}: Неподходящие пользователи</b>

Все пользователи в группе соответствуют настройкам""",
        when=~F["has_inappropriate_users"],
    ),
    ScrollingGroup(
        Select(
            Format("{item[0]}"),
            id="inappropriate_user_select",
            item_id_getter=operator.itemgetter(1),
            items="inappropriate_users",
            on_click=on_kick_inappropriate_user,
        ),
        id="inappropriate_users_scroll",
        width=1,
        height=5,
        when="has_inappropriate_users",
        hide_on_single_page=True,
    ),
    Button(
        Const("🚫 Исключить всех"),
        id="kick_all",
        on_click=on_kick_all_inappropriate_users,
        when="has_multiple_users",
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Groups.group_details),
        HOME_BTN,
    ),
    state=Groups.inappropriate_users,
    getter=inappropriate_users_getter,
)

groups_members_window = Window(
    Format(
        """👥 <b>Участники {group_type}</b>: {group_name}

📊 <b>Всего участников:</b> {members_count}
🔍 <b>Фильтр:</b> {current_filter_name}

<i>Выбери участника для просмотра детальной информации</i>""",
        when="has_members",
    ),
    Format(
        """👥 <b>Участники {group_type}</b>: {group_name}

В группе нет участников или произошла ошибка при их загрузке.""",
        when=~F["has_members"],
    ),
    ScrollingGroup(
        Select(
            Format("{item[0]}"),
            id="members_select",
            item_id_getter=operator.itemgetter(1),
            items="filtered_members",
            on_click=on_member_selected,
        ),
        id="members_scroll",
        width=1,
        height=6,
        when="has_members",
        hide_on_single_page=True,
    ),
    Group(
        Radio(
            Format("🔘 {item[1]}"),
            Format("⚪️ {item[1]}"),
            id="role_filter",
            item_id_getter=operator.itemgetter(0),
            items="available_role_filters",
            on_state_changed=on_role_filter_changed,
        ),
        width=3,
        when="has_role_filters",
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back_to_access", state=Groups.settings_access),
        HOME_BTN,
    ),
    getter=groups_members_getter,
    state=Groups.settings_members,
)


member_details_window = Window(
    Format("👤 <b>Информация об участнике</b>\n<b>Группа:</b> {group_name}\n"),
    Format("{member_info}"),
    Row(
        Button(
            Const("👤 Исключить"),
            id="kick_member",
            on_click=on_kick_member,
            when="can_kick",
        ),
        Button(
            Const("🚫 Забанить"),
            id="ban_member",
            on_click=on_ban_member,
            when="can_kick",
        ),
    ),
    Row(
        SwitchTo(
            Const("↩️ К списку"), id="back_to_members", state=Groups.settings_members
        ),
        HOME_BTN,
    ),
    getter=member_details_getter,
    state=Groups.member_details,
)

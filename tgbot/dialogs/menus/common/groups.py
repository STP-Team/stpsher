"""Генерация общих функций для управления группами."""

from typing import Any

from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import (
    Button,
    Checkbox,
    ManagedRadio,
    Radio,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format
from magic_filter import F

from tgbot.dialogs.events.common.filters import on_filter_change
from tgbot.dialogs.events.common.groups import (
    close_group_dialog,
    on_access_level_click,
    on_group_selected,
    on_members_click,
    on_remove_bot_click,
    on_service_all_toggle,
    on_service_join_toggle,
    on_service_leave_toggle,
    on_service_messages_apply,
    on_service_messages_cancel,
    on_service_other_toggle,
    on_service_photo_toggle,
    on_service_pin_toggle,
    on_service_title_toggle,
    on_service_videochat_toggle,
    on_toggle_is_casino_allowed,
    on_toggle_new_user_notify,
)
from tgbot.dialogs.getters.common.groups import (
    group_details_members_getter,
    group_details_services_getter,
    group_remove_getter,
    groups_cmds_getter,
    groups_details_getter,
    groups_list_getter,
)
from tgbot.dialogs.states.common.groups import Groups

groups_window = Window(
    Const("""👯‍♀️ <b>Группы</b>

Ты можешь использовать меня для менеджмента групп

🪄 <b>Я умею</b>
∙ Приветствовать новых пользователей
∙ Удалять уволенных
∙ Разрешать доступ к группе конкретных должностям
∙ Удалять сервисные сообщения
∙ Управлять доступом к казино в группе
∙ Просматривать список участников"""),
    Row(
        SwitchTo(
            Const("📋 Список"),
            id="groups_list",
            state=Groups.list,
        ),
        SwitchTo(Const("💡 Команды"), id="groups_cmds", state=Groups.cmds),
    ),
    Button(Const("↩️ Назад"), id="menu", on_click=close_group_dialog),
    state=Groups.menu,
)

# Окно списка групп
groups_list_window = Window(
    Format(
        "🛡️ <b>Управление группами</b>\n\nНайдено групп: <b>{groups_count}</b>\n\n<i>Выбери группу для просмотра настроек</i>",
        when="has_groups",
    ),
    Format(
        "🛡️ <b>Управление группами</b>\n\n❌ <b>Ты не состоишь ни в одной группе</b>\n\nЧтобы управлять настройками бота в группе, тебе необходимо:\n1. Вступить в группу, где добавлен бот\n2. Чтобы изменять настройки - получить права администратора\n\n<i>После добавления в группу, вернись в это меню</i>",
        when=~F["has_groups"],
    ),
    ScrollingGroup(
        Select(
            Format("{item[0]}"),
            id="groups_select",
            item_id_getter=lambda x: x[1],
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
        Button(Const("🏠 Домой"), id="home", on_click=close_group_dialog),
    ),
    getter=groups_list_getter,
    state=Groups.list,
)

# Окно настроек группы
groups_list_detail_window = Window(
    Format(
        "⚙️ <b>Настройки группы</b>: {group_name}\n\n<b>Обозначения</b>\n- 🟢 Опция включена\n- 🔴 Опция выключена\n\n<i>Используй меню для управления функциями бота в группе</i>"
    ),
    Button(
        Const("🛡️ Уровень доступа"),
        id="access_level",
        on_click=on_access_level_click,
    ),
    Row(
        Checkbox(
            Const("🟢 Приветствие"),
            Const("🔴 Приветствие"),
            id="new_user_notify",
            on_state_changed=on_toggle_new_user_notify,
        ),
        Checkbox(
            Const("🟢 Казино"),
            Const("🔴 Казино"),
            id="is_casino_allowed",
            on_state_changed=on_toggle_is_casino_allowed,
        ),
    ),
    Row(
        SwitchTo(
            Const("🗑️ Сервисные сообщения"),
            id="service_messages",
            state=Groups.settings_services,
        ),
        Button(Const("👥 Состав"), id="members", on_click=on_members_click),
    ),
    Button(Const("♻️ Удалить бота"), id="remove_bot", on_click=on_remove_bot_click),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back_to_list", state=Groups.list),
        Button(Const("🏠 Домой"), id="home", on_click=close_group_dialog),
    ),
    state=Groups.group_details,
    getter=groups_details_getter,
)

# Окно команд для групп
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
∙ <code>/mute [время]</code> - замутить пользователя (в ответ на сообщение или /mute user_id)
∙ <code>/unmute</code> - размутить пользователя (в ответ на сообщение или /unmute user_id)
∙ <code>/ban</code> - забанить пользователя (в ответ на сообщение или /ban user_id)
∙ <code>/unban</code> - разбанить пользователя (в ответ на сообщение или /unban user_id)

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
        item_id_getter=lambda item: item[0],
        items=[("user", "Пользователь"), ("admin", "Администратор")],
        on_click=on_filter_change,
    ),
    SwitchTo(Const("↩️ Назад"), id="back", state=Groups.menu),
    state=Groups.cmds,
    getter=groups_cmds_getter,
)

# Окно настройки уровня доступа группы (placeholder)
groups_access_window = Window(
    Const("🛡️ <b>Уровень доступа</b>\n\n<i>В разработке...</i>"),
    SwitchTo(Const("↩️ Назад"), id="back", state=Groups.group_details),
    state=Groups.settings_access,
)

# Окно настройки сервисных сообщений группы
groups_service_messages_window = Window(
    Const(
        """🗑️ <b>Управление сервисными сообщениями</b>

<b>Обозначения</b>
- 🟢 Удаляются
- 🔴 Не удаляются

<blockquote expandable><b>Типы сервисных сообщений:</b>
• <b>Все</b> - все сервисные сообщения
• <b>Вход</b> - "X присоединился к чату"
• <b>Выход</b> - "X покинул чат"
• <b>Прочее</b> - бусты, платежи, уведомления
• <b>Фото</b> - смена фото чата
• <b>Закреп</b> - "X закрепил сообщение"
• <b>Название</b> - смена названия чата
• <b>Видеозвонки</b> - действия с видеозвонками</blockquote>

<i>Выбери типы сообщений для удаления, затем нажми "Применить"</i>"""
    ),
    Row(
        Checkbox(
            Const("🟢 Все"),
            Const("🔴 Все"),
            id="service_all",
            on_state_changed=on_service_all_toggle,
        ),
        Checkbox(
            Const("🟢 Вход"),
            Const("🔴 Вход"),
            id="service_join",
            on_state_changed=on_service_join_toggle,
        ),
    ),
    Row(
        Checkbox(
            Const("🟢 Выход"),
            Const("🔴 Выход"),
            id="service_leave",
            on_state_changed=on_service_leave_toggle,
        ),
        Checkbox(
            Const("🟢 Прочее"),
            Const("🔴 Прочее"),
            id="service_other",
            on_state_changed=on_service_other_toggle,
        ),
    ),
    Row(
        Checkbox(
            Const("🟢 Фото"),
            Const("🔴 Фото"),
            id="service_photo",
            on_state_changed=on_service_photo_toggle,
        ),
        Checkbox(
            Const("🟢 Закреп"),
            Const("🔴 Закреп"),
            id="service_pin",
            on_state_changed=on_service_pin_toggle,
        ),
    ),
    Row(
        Checkbox(
            Const("🟢 Название"),
            Const("🔴 Название"),
            id="service_title",
            on_state_changed=on_service_title_toggle,
        ),
        Checkbox(
            Const("🟢 Видеозвонки"),
            Const("🔴 Видеозвонки"),
            id="service_videochat",
            on_state_changed=on_service_videochat_toggle,
        ),
    ),
    Row(
        Button(
            Const("✅ Применить"),
            id="apply",
            on_click=on_service_messages_apply,
            when=F["has_pending_changes"],
        ),
        Button(
            Const("❌ Отменить"),
            id="cancel",
            on_click=on_service_messages_cancel,
            when=F["has_pending_changes"],
        ),
    ),
    SwitchTo(Const("↩️ Назад"), id="back", state=Groups.group_details),
    state=Groups.settings_services,
    getter=group_details_services_getter,
)

# Окно участников группы
groups_members_window = Window(
    Format(
        "👥 <b>Состав группы</b>: {group_name}\n\nУчастников: <b>{total_members}</b>\n\n<i>В разработке...</i>"
    ),
    SwitchTo(Const("↩️ Назад"), id="back", state=Groups.group_details),
    state=Groups.settings_members,
    getter=group_details_members_getter,
)

# Окно подтверждения удаления бота из группы
groups_remove_bot_window = Window(
    Format(
        "⚠️ <b>Подтверждение удаления бота</b>\n\nГруппа: <b>{group_name}</b>\n\n<b>Что произойдет:</b>\n∙ Бот покинет группу\n∙ Группа будет удалена из базы\n∙ Все участники будут исключены из состава группы\n\n<b>Это действие необратимо!</b>\n\n<i>Функция в разработке...</i>"
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Groups.group_details),
        Button(Const("🏠 Домой"), id="home", on_click=close_group_dialog),
    ),
    state=Groups.settings_remove,
    getter=group_remove_getter,
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
    groups_members_window,
    groups_list_window,
    groups_list_detail_window,
    groups_cmds_window,
    groups_access_window,
    groups_service_messages_window,
    groups_remove_bot_window,
    on_start=on_start,
)

"""Генерация общих функций для управления группами."""

from aiogram.fsm.state import State
from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import (
    Button,
    Checkbox,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format
from magic_filter import F

from tgbot.dialogs.events.common.groups import (
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
    groups_details_getter,
    groups_list_getter,
)
from tgbot.misc.states.dialogs.gok import GokSG
from tgbot.misc.states.dialogs.head import HeadSG
from tgbot.misc.states.dialogs.mip import MipSG
from tgbot.misc.states.dialogs.root import RootSG
from tgbot.misc.states.dialogs.user import UserSG


def create_groups_window(
    state_group: RootSG | GokSG | MipSG | HeadSG | UserSG, menu_state: State
):
    """Создает окна для управления группами.

    Args:
        state_group: Группа состояний, используемая для переключения окон
        menu_state: Состояние главного меню

    Returns:
        Сгенерированный список окон для управления группами
    """
    # Основное меню групп
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
                state=state_group.groups_list,
            ),
            SwitchTo(
                Const("💡 Команды"), id="groups_cmds", state=state_group.groups_cmds
            ),
        ),
        SwitchTo(Const("↩️ Назад"), id="menu", state=menu_state),
        state=state_group.groups,
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
            SwitchTo(Const("↩️ Назад"), id="back", state=state_group.groups),
            SwitchTo(Const("🏠 Домой"), id="home", state=menu_state),
        ),
        getter=groups_list_getter,
        state=state_group.groups_list,
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
                state=state_group.groups_service_messages,
            ),
            Button(Const("👥 Состав"), id="members", on_click=on_members_click),
        ),
        Button(Const("♻️ Удалить бота"), id="remove_bot", on_click=on_remove_bot_click),
        Row(
            SwitchTo(
                Const("↩️ Назад"), id="back_to_list", state=state_group.groups_list
            ),
            SwitchTo(Const("🏠 Домой"), id="home", state=menu_state),
        ),
        state=state_group.groups_list_detail,
        getter=groups_details_getter,
    )

    # Окно команд для групп (placeholder)
    groups_cmds_window = Window(
        Const("💡 <b>Команды для групп</b>\n\n<i>В разработке...</i>"),
        SwitchTo(Const("↩️ Назад"), id="back", state=state_group.groups),
        state=state_group.groups_cmds,
    )

    # Окно настройки уровня доступа группы (placeholder)
    groups_access_window = Window(
        Const("🛡️ <b>Уровень доступа</b>\n\n<i>В разработке...</i>"),
        SwitchTo(Const("↩️ Назад"), id="back", state=state_group.groups_list_detail),
        state=state_group.groups_access,
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
        SwitchTo(Const("↩️ Назад"), id="back", state=state_group.groups_list_detail),
        state=state_group.groups_service_messages,
        getter=group_details_services_getter,
    )

    # Окно участников группы
    groups_members_window = Window(
        Format(
            "👥 <b>Состав группы</b>: {group_name}\n\nУчастников: <b>{total_members}</b>\n\n<i>В разработке...</i>"
        ),
        SwitchTo(Const("↩️ Назад"), id="back", state=state_group.groups_list_detail),
        state=state_group.groups_members,
        getter=group_details_members_getter,
    )

    # Окно подтверждения удаления бота из группы
    groups_remove_bot_window = Window(
        Format(
            "⚠️ <b>Подтверждение удаления бота</b>\n\nГруппа: <b>{group_name}</b>\n\n<b>Что произойдет:</b>\n∙ Бот покинет группу\n∙ Группа будет удалена из базы\n∙ Все участники будут исключены из состава группы\n\n<b>Это действие необратимо!</b>\n\n<i>Функция в разработке...</i>"
        ),
        Row(
            SwitchTo(Const("↩️ Назад"), id="back", state=state_group.groups_list_detail),
            SwitchTo(Const("🏠 Домой"), id="home", state=menu_state),
        ),
        state=state_group.groups_remove_bot,
        getter=group_remove_getter,
    )

    return (
        groups_window,
        groups_list_window,
        groups_list_detail_window,
        groups_cmds_window,
        groups_access_window,
        groups_service_messages_window,
        groups_members_window,
        groups_remove_bot_window,
    )

"""Обработчики для функционала управления группами."""

from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import (
    Button,
    ManagedCheckbox,
    ManagedMultiselect,
    Multiselect,
    Select,
)
from stp_database import MainRequestsRepo

from tgbot.dialogs.states.common.groups import Groups


async def start_groups_dialog(
    _callback: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик перехода в диалог групп.

    Args:
        _callback: Callback query от Telegram
        _widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.start(
        Groups.menu,
    )


async def close_groups_dialog(
    _callback: CallbackQuery,
    _button: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик возврата к главному диалогу из диалога групп.

    Args:
        _callback: Callback query от пользователя
        _button: Button виджет
        dialog_manager: Менеджер диалога
    """
    from aiogram_dialog import StartMode
    from stp_database import Employee

    from tgbot.dialogs.states.admin import AdminSG
    from tgbot.dialogs.states.gok import GokSG
    from tgbot.dialogs.states.head import HeadSG
    from tgbot.dialogs.states.mip import MipSG
    from tgbot.dialogs.states.root import RootSG
    from tgbot.dialogs.states.user import UserSG

    # Получаем пользователя из middleware_data
    user: Employee = dialog_manager.middleware_data.get("user")

    # Определяем меню на основе роли пользователя
    if user and hasattr(user, "role") and user.role:
        role = str(user.role)

        # Маппинг ролей на состояния главного меню
        role_menu_mapping = {
            "1": UserSG.menu,
            "2": HeadSG.menu,
            "3": UserSG.menu,
            "4": AdminSG.menu,
            "5": GokSG.menu,
            "6": MipSG.menu,
            "10": RootSG.menu,
        }

        menu_state = role_menu_mapping.get(role, UserSG.menu)
    else:
        # Если роль не определена, отправляем в меню по умолчанию
        menu_state = UserSG.menu

    await dialog_manager.done()
    await dialog_manager.start(menu_state, mode=StartMode.RESET_STACK)


async def on_group_selected(
    _callback: CallbackQuery,
    _widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Обработчик выбора группы из списка доступных групп.

    Меняет окно на настройки выбранной группы

    Args:
        _callback: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
        item_id: Идентификатор выбранной группы
    """
    dialog_manager.dialog_data["selected_group_id"] = int(item_id)
    await dialog_manager.switch_to(Groups.group_details)


async def on_role_selected(
    _callback: CallbackQuery,
    _widget: Multiselect,
    dialog_manager: DialogManager,
    _item_id: str,
) -> None:
    """Обработчик изменения уровня доступа к группе через Multiselect.

    Сохраняет выбранные роли в БД в формате JSON.

    Args:
        _callback: Callback query от Telegram
        _widget: Виджет Multiselect
        dialog_manager: Менеджер диалога
        _item_id: ID выбранной/снятой роли (роль, на которую кликнули)
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    group_id = dialog_manager.dialog_data.get("selected_group_id")

    # Получаем все выбранные роли из мультиселекта
    access_level_select: ManagedMultiselect = dialog_manager.find("access_level_select")
    selected_roles_str = access_level_select.get_checked()
    selected_roles = [int(role_id) for role_id in selected_roles_str]

    await stp_repo.group.update_group(group_id=group_id, allowed_roles=selected_roles)


async def on_service_message_selected(
    _callback: CallbackQuery,
    _widget: Any,
    dialog_manager: DialogManager,
    _item_id: str,
    **_kwargs: Any,
) -> None:
    """Обработчик изменения типов удаляемых сервисных сообщений через Multiselect.

    Сохраняет выбранные типы сообщений в БД.

    Args:
        _callback: Callback query от Telegram
        _widget: Виджет Multiselect
        dialog_manager: Менеджер диалога
        _item_id: ID выбранного/снятого типа сообщения
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    group_id = dialog_manager.dialog_data.get("selected_group_id")

    # Получаем все выбранные типы сервисных сообщений из мультиселекта
    service_messages_select: ManagedMultiselect = dialog_manager.find(
        "service_messages_select"
    )
    selected_messages = list(service_messages_select.get_checked())

    await stp_repo.group.update_group(
        group_id=group_id, service_messages=selected_messages
    )


async def _toggle_group_setting(
    event: CallbackQuery,
    dialog_manager: DialogManager,
    widget: ManagedCheckbox,
    field_name: str,
    success_message: str,
) -> None:
    """Общий обработчик переключаемых настроек группы.

    Args:
        event: Событие клика на кнопку меню настроек
        dialog_manager: Менеджер диалога
        widget: Виджет чекбокса
        field_name: Название настройки
        success_message: Текст сообщения об успешном изменении
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    group_id = dialog_manager.dialog_data.get("selected_group_id")

    group = await stp_repo.group.get_groups(group_id=group_id)
    new_value = widget.is_checked()
    current_value = getattr(group, field_name, None)

    if current_value != new_value:
        await stp_repo.group.update_group(group_id=group_id, **{field_name: new_value})
        await event.answer(
            f"✅ {success_message}: {'включено' if new_value else 'выключено'}"
        )


async def on_toggle_only_employees(
    event: CallbackQuery,
    widget: ManagedCheckbox,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик изменения настройки удаления не сотрудников.

    Args:
        event: Событие клика на кнопку настройки
        widget: Виджет чекбокса
        dialog_manager: Менеджер диалога
    """
    await _toggle_group_setting(
        event,
        dialog_manager,
        widget,
        "remove_unemployed",
        "Удаление не сотрудников",
    )


async def on_toggle_new_user_notify(
    event: CallbackQuery,
    widget: ManagedCheckbox,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик изменения настройки уведомления о новых пользователях в группе.

    Args:
        event: Событие клика на кнопку настройки
        widget: Виджет чекбокса
        dialog_manager: Менеджер диалога
    """
    await _toggle_group_setting(
        event,
        dialog_manager,
        widget,
        "new_user_notify",
        "Приветствие новых участников",
    )


async def on_toggle_is_casino_allowed(
    event: CallbackQuery,
    widget: ManagedCheckbox,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик изменения настройки доступа к казино.

    Args:
        event: Событие клика на кнопку настройки
        widget: Виджет чекбокса
        dialog_manager: Менеджер диалога
    """
    await _toggle_group_setting(
        event, dialog_manager, widget, "is_casino_allowed", "Казино"
    )


async def on_confirm_delete_group(
    callback: CallbackQuery,
    _button: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик подтверждения удаления группы и бота из нее.

    Удаляет всех участников группы, удаляет группу из БД,
    бот покидает группу и возвращает пользователя к списку групп.

    Args:
        callback: Callback query от Telegram
        _button: Button виджет
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    group_id = dialog_manager.dialog_data.get("selected_group_id")

    try:
        # Удаляем всех участников группы
        await stp_repo.group_member.remove_all_members(group_id)

        # Удаляем саму группу из БД
        await stp_repo.group.delete_group(group_id)

        # Бот покидает группу
        await callback.bot.leave_chat(chat_id=group_id)

        await callback.answer(
            "✅ Бот успешно удален из группы, все данные очищены", show_alert=True
        )

        # Возвращаемся к списку групп
        await dialog_manager.switch_to(Groups.menu)

    except Exception as e:
        await callback.answer(
            f"❌ Ошибка при удалении бота из группы: {str(e)}", show_alert=True
        )

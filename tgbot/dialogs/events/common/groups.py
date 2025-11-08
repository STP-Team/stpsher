"""Обработчики для функционала управления группами."""

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
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик перехода в диалог групп.

    Args:
        _event: Callback query от Telegram
        _widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.start(
        Groups.menu,
    )


async def on_group_selected(
    _event: CallbackQuery,
    _widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Обработчик выбора группы из списка доступных групп.

    Меняет окно на настройки выбранной группы

    Args:
        _event: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
        item_id: Идентификатор выбранной группы
    """
    dialog_manager.dialog_data["group_id"] = int(item_id)
    await dialog_manager.switch_to(Groups.group_details)


async def on_role_selected(
    _event: CallbackQuery,
    _widget: Multiselect,
    dialog_manager: DialogManager,
    _item_id: str,
) -> None:
    """Обработчик изменения уровня доступа к группе через Multiselect.

    Сохраняет выбранные роли в БД в формате JSON.

    Args:
        _event: Callback query от Telegram
        _widget: Виджет Multiselect
        dialog_manager: Менеджер диалога
        _item_id: ID выбранной/снятой роли (роль, на которую кликнули)
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    group_id = dialog_manager.dialog_data.get("group_id")

    # Получаем все выбранные роли из мультиселекта
    access_level_select: ManagedMultiselect = dialog_manager.find("access_level_select")
    selected_roles_str = access_level_select.get_checked()
    selected_roles = [int(role_id) for role_id in selected_roles_str]

    await stp_repo.group.update_group(group_id=group_id, allowed_roles=selected_roles)


async def on_service_message_selected(
    _event: CallbackQuery,
    _widget: ManagedMultiselect,
    dialog_manager: DialogManager,
    _item_id: str,
    **_kwargs,
) -> None:
    """Обработчик изменения типов удаляемых сервисных сообщений через Multiselect.

    Сохраняет выбранные типы сообщений в БД.

    Args:
        _event: Callback query от Telegram
        _widget: Виджет Multiselect
        dialog_manager: Менеджер диалога
        _item_id: ID выбранного/снятого типа сообщения
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    group_id = dialog_manager.dialog_data.get("group_id")

    # Получаем все выбранные типы сервисных сообщений из мультиселекта
    service_messages_select: ManagedMultiselect = dialog_manager.find(
        "service_messages_select"
    )
    selected_messages = list(service_messages_select.get_checked())

    await stp_repo.group.update_group(
        group_id=group_id, service_messages=selected_messages
    )


async def on_only_employees_click(
    _event: CallbackQuery,
    widget: ManagedCheckbox,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик изменения настройки удаления не сотрудников.

    Args:
        _event: Событие клика на кнопку настройки
        widget: Виджет чекбокса
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    group_id = dialog_manager.dialog_data.get("group_id")

    await stp_repo.group.update_group(
        group_id=group_id, remove_unemployed=not widget.is_checked()
    )


async def on_new_user_notify_click(
    _event: CallbackQuery,
    widget: ManagedCheckbox,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик изменения настройки уведомления о новых пользователях в группе.

    Args:
        _event: Событие клика на кнопку настройки
        widget: Виджет чекбокса
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    group_id = dialog_manager.dialog_data.get("group_id")

    await stp_repo.group.update_group(
        group_id=group_id, new_user_notify=not widget.is_checked()
    )


async def on_is_casino_allowed_click(
    _event: CallbackQuery,
    widget: ManagedCheckbox,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик изменения настройки доступа к казино.

    Args:
        _event: Событие клика на кнопку настройки
        widget: Виджет чекбокса
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    group_id = dialog_manager.dialog_data.get("group_id")

    await stp_repo.group.update_group(
        group_id=group_id, is_casino_allowed=not widget.is_checked()
    )


async def on_confirm_delete_group(
    event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик подтверждения удаления группы и бота из нее.

    Удаляет всех участников группы, удаляет группу из БД,
    бот покидает группу и возвращает пользователя к списку групп.

    Args:
        event: Callback query от Telegram
        _widget: Button виджет
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    group_id = dialog_manager.dialog_data.get("group_id")

    try:
        # Удаляем всех участников группы
        await stp_repo.group_member.remove_all_members(group_id)

        # Удаляем саму группу из БД
        await stp_repo.group.delete_group(group_id)

        # Бот покидает группу
        await event.bot.leave_chat(chat_id=group_id)

        await event.answer(
            "✅ Бот успешно удален из группы, все данные очищены", show_alert=True
        )

        # Возвращаемся к списку групп
        await dialog_manager.switch_to(Groups.menu)

    except Exception as e:
        await event.answer(
            f"❌ Ошибка при удалении бота из группы: {str(e)}", show_alert=True
        )

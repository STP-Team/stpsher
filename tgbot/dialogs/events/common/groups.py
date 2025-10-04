"""Обработчики для функционала управления группами."""

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, ManagedCheckbox, Select

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.dialogs.states.common.groups import Groups

# Храним применяемые изменения в памяти
pending_role_changes: dict[int, list[str]] = {}
pending_service_messages_changes: dict[int, list[str]] = {}


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


async def close_group_dialog(
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
    await dialog_manager.done()


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

    if not group_id:
        return

    new_value = widget.is_checked()
    updated_group = await stp_repo.group.update_group(
        group_id=group_id, **{field_name: new_value}
    )

    if updated_group:
        status = "включено" if new_value else "выключено"
        await event.answer(f"{success_message} {status}")
    else:
        await event.answer("❌ Ошибка при обновлении настройки")


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


async def on_access_level_click(
    callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
) -> None:
    """Обработчик изменения настройки уровней доступа к группе.

    Args:
        callback: Callback query от Telegram
        _button: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    group_id = dialog_manager.dialog_data.get("selected_group_id")

    if not group_id:
        return

    group = await stp_repo.group.get_group(group_id)
    if not group:
        await callback.answer("❌ Группа не найдена")
        return

    # Инициализируем временные изменения
    pending_role_changes[group_id] = (group.allowed_roles or []).copy()

    await dialog_manager.switch_to(Groups.settings_access)


async def on_members_click(
    _callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
) -> None:
    """Обработчик открытия списка участников группы.

    Args:
        _callback: Callback query от Telegram
        _button: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    group_id = dialog_manager.dialog_data.get("selected_group_id")

    if not group_id:
        return

    await dialog_manager.switch_to(Groups.settings_members)


async def on_remove_bot_click(
    _callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
):
    """Обработчик удаления бота из группы.

    Args:
        _callback: Callback query от Telegram
        _button: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    group_id = dialog_manager.dialog_data.get("selected_group_id")

    if not group_id:
        return

    await dialog_manager.switch_to(Groups.settings_remove)


async def _initialize_pending_service_messages(
    group_id: int, dialog_manager: DialogManager
) -> None:
    """Инициализация временных изменений удаления сервисных сообщений.

    Args:
        group_id: Идентификатор группы Telegram
        dialog_manager: Менеджер диалога
    """
    if group_id not in pending_service_messages_changes:
        stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
        group = await stp_repo.group.get_group(group_id)
        pending_service_messages_changes[group_id] = (
            getattr(group, "service_messages", []) or []
        ).copy()


def create_service_message_toggle_handler(category: str, category_name: str):
    """Создает обработчик для каждого вида сервисных сообщений.

    Args:
        category: Оригинальные название группы категории
        category_name: Название группы категории для отображения
    """

    async def handler(
        event: CallbackQuery,
        checkbox: ManagedCheckbox,
        dialog_manager: DialogManager,
    ):
        """Handle service message category toggle."""
        group_id = dialog_manager.dialog_data.get("selected_group_id")

        if not group_id:
            return

        current_pending = pending_service_messages_changes[group_id]
        is_checked = checkbox.is_checked()

        if is_checked and category not in current_pending:
            pending_service_messages_changes[group_id] = current_pending + [category]
        elif not is_checked and category in current_pending:
            pending_service_messages_changes[group_id] = [
                c for c in current_pending if c != category
            ]

        status = "добавлена к удаляемым" if is_checked else "убрана из удаляемых"
        await event.answer(f"Категория '{category_name}' {status}")

    return handler


# Создаем обработчики для каждого типа сервисных сообщений
on_service_all_toggle = create_service_message_toggle_handler("all", "Все сообщения")
on_service_join_toggle = create_service_message_toggle_handler(
    "join", "Вход пользователей"
)
on_service_leave_toggle = create_service_message_toggle_handler(
    "leave", "Выход пользователей"
)
on_service_other_toggle = create_service_message_toggle_handler(
    "other", "Прочие сообщения"
)
on_service_photo_toggle = create_service_message_toggle_handler("photo", "Смена фото")
on_service_pin_toggle = create_service_message_toggle_handler(
    "pin", "Закрепленные сообщения"
)
on_service_title_toggle = create_service_message_toggle_handler(
    "title", "Смена названия"
)
on_service_videochat_toggle = create_service_message_toggle_handler(
    "videochat", "Видеозвонки"
)


async def on_service_messages_apply(
    callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
) -> None:
    """Обработчик применения временных настроек удаления сервисных сообщений.

    Args:
        callback: Callback query от Telegram
        _button: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    group_id = dialog_manager.dialog_data.get("selected_group_id")

    if not group_id:
        return

    if group_id not in pending_service_messages_changes:
        await callback.answer("Нет изменений для применения")
        return

    new_categories = pending_service_messages_changes[group_id]
    updated_group = await stp_repo.group.update_group(
        group_id=group_id, service_messages=new_categories
    )

    if updated_group:
        await callback.answer("✅ Настройки сервисных сообщений применены!")
        del pending_service_messages_changes[group_id]
    else:
        await callback.answer("❌ Ошибка при применении настроек")


async def on_service_messages_cancel(
    callback: CallbackQuery, _button: Button, dialog_manager: DialogManager
) -> None:
    """Обработчик отмены применения временных изменений удаления сервисных сообщений.

    Args:
        callback: Callback query от Telegram
        _button: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    group_id = dialog_manager.dialog_data.get("selected_group_id")

    if not group_id:
        return

    if group_id in pending_service_messages_changes:
        del pending_service_messages_changes[group_id]

    await callback.answer("❌ Изменения отменены")

    current_state = dialog_manager.current_context().state.group
    await dialog_manager.switch_to(current_state.groups_list_detail)

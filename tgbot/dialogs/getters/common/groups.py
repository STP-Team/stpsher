"""Геттеры для групповых окон."""

import logging
from typing import Any, Dict

from aiogram import Bot
from aiogram_dialog import DialogManager

from infrastructure.database.repo.STP.requests import MainRequestsRepo

pending_role_changes = {}
pending_service_messages_changes = {}

logger = logging.getLogger(__name__)


async def get_user_groups(user_id: int, stp_repo: MainRequestsRepo, bot: Bot) -> tuple:
    """Получает список групп, где пользователь является участником.

    Args:
        user_id: Идентификатор Telegram пользователя, запрашивающего список групп
        stp_repo: Репозиторий операций с базой STP
        bot: Экземпляр бота

    Returns:
        Кортеж групп пользователя, в которых он числится участником в базе данных
    """
    admin_groups = []
    member_groups_list = []
    admin_status = {}

    member_groups = await stp_repo.group_member.get_member_groups(user_id)

    for group_member in member_groups:
        group_id = group_member.group_id
        try:
            try:
                chat_info = await bot.get_chat(chat_id=group_id)
                group_name = chat_info.title or f"{group_id}"

                is_admin = await is_user_group_admin(user_id, group_id, bot)
                admin_status[group_id] = is_admin

                if is_admin:
                    admin_groups.append((group_id, group_name))
                else:
                    member_groups_list.append((group_id, group_name))

            except Exception as e:
                logger.warning(f"Failed to get chat info for group {group_id}: {e}")
                group_name = f"{group_id}"
                is_admin = await is_user_group_admin(user_id, group_id, bot)
                admin_status[group_id] = is_admin

                if is_admin:
                    admin_groups.append((group_id, group_name))
                else:
                    member_groups_list.append((group_id, group_name))

        except Exception as e:
            logger.warning(f"Failed to check group {group_id}: {e}")
            continue

    sorted_groups = admin_groups + member_groups_list
    return sorted_groups, admin_status


async def is_user_group_admin(user_id: int, group_id: int, bot: Bot) -> bool:
    """Проверяет есть ли у пользователя права администратора в группе.

    Args:
        user_id: Идентификатор Telegram пользователя
        group_id: Идентификатор проверяемой Telegram группы
        bot: Экземпляр бота

    Returns:
        True если пользователь является администраторов в группе, иначе False
    """
    try:
        member_status = await bot.get_chat_member(chat_id=group_id, user_id=user_id)
        return member_status.status in ["administrator", "creator"]
    except Exception as e:
        logger.warning(f"Failed to check admin status for group {group_id}: {e}")
        return False


async def groups_list_getter(
    stp_repo: MainRequestsRepo, dialog_manager: DialogManager, bot: Bot, **_kwargs
) -> Dict[str, Any]:
    """Получает информацию о списке групп для окна групп.

    Args:
        bot: Экземпляр бота
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь групп пользователя, в которых он числится участником в базе данных
    """
    user_id = dialog_manager.event.from_user.id

    user_groups, admin_status = await get_user_groups(user_id, stp_repo, bot)

    groups_items = []
    for group_id, group_name in user_groups:
        is_admin = admin_status.get(group_id, False)
        emoji = (
            "🛡️" if is_admin else "👤"
        )  # Отображение роли в группе: Участник или администратор
        display_name = group_name[:30] + "..." if len(group_name) > 30 else group_name
        groups_items.append((f"{emoji} {display_name}", group_id))

    return {
        "groups_count": len(user_groups),
        "has_groups": len(user_groups) > 0,
        "groups": groups_items,
    }


async def groups_details_getter(
    dialog_manager: DialogManager, stp_repo: MainRequestsRepo, bot: Bot, **_kwargs
) -> Dict[str, Any]:
    """Получаем информацию о выбранной пользователем группе в списке групп.

    Args:
        bot: Экземпляр бота
        dialog_manager: Менеджер диалога
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь с информацией о выбранной группе
    """
    group_id = dialog_manager.dialog_data.get("selected_group_id")

    if not group_id:
        return {"error": True}

    group = await stp_repo.group.get_group(group_id)
    if not group:
        return {"error": True}

    try:
        chat_info = await bot.get_chat(chat_id=group_id)
        group_name = chat_info.title or f"{group_id}"
    except Exception:
        group_name = f"ID: {group_id}"

    widget_data = dialog_manager.dialog_data.setdefault("__aiogd_widget_data__", {})
    widget_data["new_user_notify"] = group.new_user_notify
    widget_data["is_casino_allowed"] = group.is_casino_allowed

    return {
        "group_name": group_name,
        "group_id": group_id,
        "remove_unemployed": group.remove_unemployed,
        "new_user_notify": group.new_user_notify,
        "is_casino_allowed": group.is_casino_allowed,
        "has_access_roles": bool(group.allowed_roles),
        "has_service_messages": bool(getattr(group, "service_messages", [])),
    }


async def group_details_members_getter(
    dialog_manager: DialogManager, stp_repo: MainRequestsRepo, bot: Bot, **_kwargs
) -> Dict[str, Any]:
    """Получает список участников группы из базы данных для отображения.

    Args:
        bot: Экземпляр бота
        dialog_manager: Менеджер диалога
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь участников группы из базы данных
    """
    group_id = dialog_manager.dialog_data.get("selected_group_id")

    if not group_id:
        return {"error": True}

    group = await stp_repo.group.get_group(group_id)
    if not group:
        return {"error": True}

    try:
        chat_info = await bot.get_chat(chat_id=group_id)
        group_name = chat_info.title or f"{group_id}"
    except Exception:
        group_name = f"ID: {group_id}"

    group_members = await stp_repo.group_member.get_group_members(group_id)

    employees = []
    non_employee_users = []

    for group_member in group_members:
        employee = await stp_repo.employee.get_user(user_id=group_member.member_id)
        if employee:
            employees.append(employee)
        else:
            try:
                chat_member = await bot.get_chat_member(
                    chat_id=group_id, user_id=group_member.member_id
                )
                non_employee_users.append(chat_member.user)
            except Exception:
                continue

    total_members = len(employees) + len(non_employee_users)

    return {
        "group_name": group_name,
        "group_id": group_id,
        "total_members": total_members,
        "employees": employees,
        "users": non_employee_users,
    }


async def group_details_services_getter(
    dialog_manager: DialogManager, stp_repo: MainRequestsRepo, bot: Bot, **_kwargs
) -> Dict[str, Any]:
    """Получает информацию для окна настройки сервисных сообщений.

    Args:
        bot: Экземпляр бота
        dialog_manager: Менеджер диалога
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь настроек сервисных сообщений группы
    """
    group_id = dialog_manager.dialog_data.get("selected_group_id")

    if not group_id:
        return {"error": True}

    group = await stp_repo.group.get_group(group_id)
    if not group:
        return {"error": True}

    try:
        chat_info = await bot.get_chat(chat_id=group_id)
        group_name = chat_info.title or f"{group_id}"
    except Exception:
        group_name = f"ID: {group_id}"

    # Initialize pending changes if not exists
    if group_id not in pending_service_messages_changes:
        pending_service_messages_changes[group_id] = (
            getattr(group, "service_messages", []) or []
        ).copy()

    current_pending = pending_service_messages_changes[group_id]

    # Initialize checkbox states
    widget_data = dialog_manager.dialog_data.setdefault("__aiogd_widget_data__", {})
    widget_data["service_all"] = "all" in current_pending
    widget_data["service_join"] = "join" in current_pending
    widget_data["service_leave"] = "leave" in current_pending
    widget_data["service_other"] = "other" in current_pending
    widget_data["service_photo"] = "photo" in current_pending
    widget_data["service_pin"] = "pin" in current_pending
    widget_data["service_title"] = "title" in current_pending
    widget_data["service_videochat"] = "videochat" in current_pending

    return {
        "group_name": group_name,
        "group_id": group_id,
        "has_pending_changes": current_pending
        != (getattr(group, "service_messages", []) or []),
    }


async def groups_cmds_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Получает данные для окна команд групп.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с информацией о выбранном фильтре команд
    """
    filter_value = dialog_manager.dialog_data.get("groups_cmds_filter", "user")

    return {
        "is_user": filter_value == "user",
    }


async def group_remove_getter(
    dialog_manager: DialogManager, stp_repo: MainRequestsRepo, bot: Bot, **_kwargs
) -> Dict[str, Any]:
    """Получает данные для окна подтверждения удаления бота из группы.

    Args:
        bot: Экземпляр бота
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с group_name и group_id
    """
    group_id = dialog_manager.dialog_data.get("selected_group_id")

    if not group_id:
        return {"error": True}

    group = await stp_repo.group.get_group(group_id)
    if not group:
        return {"error": True}

    try:
        chat_info = await bot.get_chat(chat_id=group_id)
        group_name = chat_info.title or f"{group_id}"
    except Exception:
        group_name = f"ID: {group_id}"

    return {
        "group_name": group_name,
        "group_id": group_id,
    }

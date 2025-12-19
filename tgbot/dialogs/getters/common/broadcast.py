"""Геттеры для окон рассылки."""

from aiogram_dialog import DialogManager
from sqlalchemy import distinct, select
from stp_database.models.STP import Employee
from stp_database.repo.STP import MainRequestsRepo

from tgbot.misc.dicts import roles
from tgbot.misc.helpers import format_fullname, short_name, strftime_date


async def broadcast_select_getter(
    dialog_manager: DialogManager, stp_repo: MainRequestsRepo, **_kwargs
):
    """Получает список направлений или групп руководителей для выбора в рассылке.

    Args:
        dialog_manager: Менеджер диалога
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь с items для Multiselect виджета
    """
    broadcast_type = dialog_manager.dialog_data.get("broadcast_type")
    selected_filter = dialog_manager.dialog_data.get("broadcast_filter")

    if broadcast_type == "by_division":
        # Получаем уникальные направления из базы
        query = select(distinct(Employee.division)).where(
            Employee.division.isnot(None), Employee.division != ""
        )
        result = await stp_repo.session.execute(query)
        divisions = result.scalars().all()

        items = [(division, division) for division in sorted(divisions)]
        title = "Выбери направления для рассылки"
        broadcast_filters = []

    elif broadcast_type == "by_group":
        # Получаем всех руководителей
        heads = await stp_repo.employee.get_users(roles=2)

        # Фильтруем руководителей по выбранному направлению
        if selected_filter and selected_filter != "all":
            heads = [head for head in heads if head.division == selected_filter]

        items = []
        for head in heads:
            display_name = short_name(head.fullname)
            items.append((head.id, display_name))

        # Получаем уникальные направления руководителей для фильтрации
        all_heads = await stp_repo.employee.get_users(roles=2)
        head_divisions = sorted({
            head.division for head in all_heads if head.division is not None
        })
        broadcast_filters = [("all", "Все")] + [(div, div) for div in head_divisions]

        title = "Выбери группы руководителей для рассылки"
    elif broadcast_type == "by_role":
        # Получаем роли из словаря, исключая роль 0 (Не авторизован)
        items = [
            (str(role_id), f"{role_data['emoji']} {role_data['name']}")
            for role_id, role_data in roles.items()
            if role_id != 0
        ]
        title = "Выбери уровни доступа для рассылки"
        broadcast_filters = []
    else:
        items = []
        broadcast_filters = []
        title = "Ошибка: неизвестный тип рассылки"

    return {
        "items": items,
        "title": title,
        "broadcast_type": broadcast_type,
        "broadcast_filters": broadcast_filters,
    }


async def broadcast_info_getter(
    dialog_manager: DialogManager, stp_repo: MainRequestsRepo, **_kwargs
):
    """Получает информацию о рассылке для отображения.

    Args:
        dialog_manager: Менеджер диалога
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь с информацией о рассылке
    """
    broadcast_type_raw = dialog_manager.dialog_data.get("broadcast_type", None)
    broadcast_text = dialog_manager.dialog_data.get("broadcast_text", None)
    broadcast_items = dialog_manager.dialog_data.get("broadcast_items", [])

    broadcast_type = None
    broadcast_targets = None

    if broadcast_type_raw is not None:
        match broadcast_type_raw:
            case "by_division":
                broadcast_type = "🔰 По направлению"
                if broadcast_items:
                    broadcast_targets = ", ".join(broadcast_items)
            case "by_group":
                broadcast_type = "👔 По группам"
                if broadcast_items:
                    # Получаем полные имена руководителей по их ID и отображаем в коротком формате
                    short_names = []
                    for head_id in broadcast_items:
                        head = await stp_repo.employee.get_users(main_id=int(head_id))
                        if head:
                            short_names.append(
                                format_fullname(
                                    head,
                                    True,
                                    True,
                                )
                            )
                    broadcast_targets = ", ".join(short_names)
            case "by_role":
                broadcast_type = "🛡️ По уровню доступа"
                if broadcast_items:
                    # Получаем названия ролей по их ID
                    role_names = []
                    for role_id in broadcast_items:
                        role_data = roles.get(int(role_id))
                        if role_data:
                            role_names.append(
                                f"{role_data['emoji']} {role_data['name']}"
                            )
                    broadcast_targets = ", ".join(role_names)
            case "all":
                broadcast_type = "🌎 Всем"

    return {
        "broadcast_type": broadcast_type,
        "broadcast_text": broadcast_text,
        "broadcast_targets": broadcast_targets,
        "has_targets": broadcast_targets is not None,
    }


async def broadcast_progress_getter(dialog_manager: DialogManager, **_kwargs):
    """Получает информацию о прогрессе рассылки.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с информацией о прогрессе для Progress виджета
    """
    current = dialog_manager.dialog_data.get("current_progress", 0)
    total = dialog_manager.dialog_data.get("total_users", 0)

    # Вычисляем процент для Progress виджета (0-100)
    progress = int((current / total * 100)) if total > 0 else 0

    return {
        "current": current,
        "total": total,
        "progress": progress,
    }


async def broadcast_result_getter(
    dialog_manager: DialogManager, stp_repo: MainRequestsRepo, **_kwargs
):
    """Получает результаты рассылки.

    Args:
        dialog_manager: Менеджер диалога
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь с результатами рассылки
    """
    success = dialog_manager.dialog_data.get("success_count", 0)
    errors = dialog_manager.dialog_data.get("error_count", 0)
    total = dialog_manager.dialog_data.get("total_users", 0)
    failed_user_ids = dialog_manager.dialog_data.get("failed_user_ids", [])

    # Получаем информацию о пользователях, которым не удалось отправить сообщение
    failed_users = []
    failed_users_formatted = []
    for index, user_id in enumerate(failed_user_ids, 1):
        user = await stp_repo.employee.get_users(user_id=int(user_id))
        if user:
            failed_users.append(user)
            # Форматируем имя пользователя для отображения с нумерацией
            formatted_name = f"{index}. {format_fullname(user, short=True, gender_emoji=True)} ({user.division})"
            failed_users_formatted.append(formatted_name)

    return {
        "success_count": success,
        "error_count": int(errors),
        "total_users": total,
        "failed_users": failed_users,
        "failed_users_formatted": failed_users_formatted,
        "failed_users_text": "\n".join(failed_users_formatted)
        if failed_users_formatted
        else "Нет",
    }


async def broadcast_history_getter(
    stp_repo: MainRequestsRepo, **_kwargs
) -> dict[str, list[dict]]:
    """Геттер для получения списка рассылок.

    Args:
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь со списком рассылок из базы данных
    """
    broadcasts = await stp_repo.broadcast.get_broadcasts()
    dict_broadcasts = [
        {
            "id": broadcast.id,
            "target": broadcast.target or "Неизвестно",
            "recipients_length": len(broadcast.recipients or []),
            "created_at": broadcast.created_at.strftime(strftime_date)
            if broadcast.created_at
            else "",
        }
        for broadcast in broadcasts
    ]

    return {
        "broadcasts": dict_broadcasts,
    }


async def broadcast_detail_getter(
    dialog_manager: DialogManager, stp_repo: MainRequestsRepo, **_kwargs
) -> dict[str, str]:
    """Геттер для получения детальной информации о рассылке.

    Args:
        dialog_manager: Менеджер диалога
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь с детальной информацией о рассылке
    """
    broadcast_id = dialog_manager.dialog_data.get("selected_broadcast_id")
    broadcast = await stp_repo.broadcast.get_broadcasts(broadcast_id)

    if not broadcast:
        return {
            "broadcast_type": "Неизвестно",
            "broadcast_target": "Неизвестно",
            "broadcast_text": "Рассылка не найдена",
            "recipients_count": 0,
            "created_at": "",
        }

    # Определяем тип рассылки для отображения
    broadcast_type = None
    if broadcast.type == "division":
        if broadcast.target == "all":
            broadcast_type = "🌎 Всем"
        else:
            broadcast_type = "🔰 По направлению"
    elif broadcast.type == "groups":
        broadcast_type = "👔 По группам"
    elif broadcast.type == "role":
        broadcast_type = "🛡️ По уровню доступа"

    # Форматируем дату
    created_at_str = (
        broadcast.created_at.strftime(strftime_date) if broadcast.created_at else ""
    )

    # Получаем информацию о создателе рассылки
    creator = await stp_repo.employee.get_users(user_id=int(broadcast.user_id))

    return {
        "broadcast_type": broadcast_type,
        "broadcast_target": broadcast.target,
        "broadcast_text": broadcast.text,
        "recipients_count": len(broadcast.recipients or []),
        "created_at": created_at_str,
        "creator_name": format_fullname(creator, True, True),
    }

"""Геттеры для функционала управления группами."""

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
)
from aiogram.utils.deep_linking import create_startgroup_link
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import ManagedCheckbox, ManagedMultiselect
from stp_database import Employee, MainRequestsRepo

from tgbot.misc.dicts import roles
from tgbot.misc.helpers import format_fullname


async def groups_getter(bot: Bot, **_kwargs) -> dict:
    """Геттер для главного меню групп.

    Args:
        bot: Экземпляр бота

    Returns:
        Словарь с диплинком на приглашение бота
    """
    link = await create_startgroup_link(bot, "start")

    return {"joinchat_deeplink": link}


async def groups_list_getter(
    stp_repo: MainRequestsRepo,
    user: Employee,
    bot: Bot,
    **_kwargs,
) -> dict:
    """Геттер списка групп, где пользователь является администратором.

    Args:
        stp_repo: Репозиторий операций с базой STP
        user: Экземпляр пользователя с моделью Employee
        bot: Экземпляр бота

    Returns:
        Словарь со списком групп, где пользователь является администратором,
        количеством групп и флагом наличия групп
    """
    user_groups = await stp_repo.group_member.get_member_groups(member_id=user.user_id)
    managed_groups = []
    managed_groups_with_type = []

    for group in user_groups:
        try:
            chat = await bot.get_chat(chat_id=group.group_id)
            group_admins = await bot.get_chat_administrators(chat_id=group.group_id)
            admin_ids = [admin.user.id for admin in group_admins]
            if user.user_id in admin_ids:
                # Получаем информацию о чате для отображения названия
                group = await stp_repo.group.get_groups(group.group_id)
                group_name = (
                    f"{'👥' if group.group_type == 'group' else '📢'} {chat.title}"
                    or "Без названия"
                )
                managed_groups.append((group_name, str(group.group_id)))
                managed_groups_with_type.append((
                    group_name,
                    str(group.group_id),
                    group.group_type,
                ))
        except (TelegramBadRequest, TelegramForbiddenError, TelegramAPIError):
            # Пропускаем группы, где бот больше не имеет доступа
            continue

    return {
        "groups": managed_groups,
        "groups_count": len([
            group for group in managed_groups_with_type if group[2] == "group"
        ]),
        "channels_count": len([
            group for group in managed_groups_with_type if group[2] == "channel"
        ]),
        "has_groups": len(managed_groups) > 0,
    }


async def groups_details_getter(
    stp_repo: MainRequestsRepo,
    bot: Bot,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict:
    """Геттер получения настроек группы.

    Args:
        stp_repo: Репозиторий операций с базой STP
        bot: Экземпляр бота
        dialog_manager:
        **_kwargs:

    Returns:
        Словарь с информацией о выбранной группе
    """
    group_id = dialog_manager.dialog_data.setdefault(
        "group_id",
        dialog_manager.start_data.get("group_id")
        if dialog_manager.start_data
        else None,
    )

    try:
        chat = await bot.get_chat(chat_id=group_id)
    except (TelegramBadRequest, TelegramForbiddenError, TelegramAPIError) as e:
        # Возвращаем данные с информацией об ошибке
        return {
            "group_name": f"ID: {group_id}",
            "group_id": group_id,
            "is_channel": False,
            "group_type": "группы",
            "error": str(e),
        }

    settings = await stp_repo.group.get_groups(group_id=group_id)

    # Установка флага инициализации для предотвращения обновления БД
    dialog_manager.dialog_data["initializing_checkboxes"] = True

    # Установка настроек из БД
    autoapply_checkbox: ManagedCheckbox = dialog_manager.find("autoapply_checkbox")
    await autoapply_checkbox.set_checked(settings.auto_apply)

    new_user_notify_checkbox: ManagedCheckbox = dialog_manager.find("new_user_notify")
    await new_user_notify_checkbox.set_checked(settings.new_user_notify)

    is_casino_allowed: ManagedCheckbox = dialog_manager.find("is_casino_allowed")
    await is_casino_allowed.set_checked(settings.is_casino_allowed)

    # Сброс флага инициализации
    dialog_manager.dialog_data["initializing_checkboxes"] = False

    return {
        "group_name": chat.title,
        "group_id": chat.id,
        "is_channel": settings.group_type == "channel",
        "group_type": "канала" if settings.group_type == "channel" else "группы",
    }


async def group_details_access_getter(
    stp_repo: MainRequestsRepo,
    bot: Bot,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict:
    """Геттер для окна настройки уровня доступа к группе.

    Args:
        stp_repo: Репозиторий операций с базой STP
        bot: Экземпляр бота
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с данными для окна
    """
    group_id = dialog_manager.dialog_data["group_id"]

    try:
        chat = await bot.get_chat(chat_id=group_id)
    except (TelegramBadRequest, TelegramForbiddenError, TelegramAPIError) as e:
        return {
            "group_name": f"ID: {group_id}",
            "roles": [],
            "has_pending_changes": False,
            "has_inappropriate_users": False,
            "error": str(e),
        }

    settings = await stp_repo.group.get_groups(group_id=group_id)

    # Преобразуем словарь ролей в список кортежей (role_id, display_name)
    roles_list = [
        (
            role_id,
            f"{role_data['emoji']} {role_data['name']}".strip()
            if role_data["emoji"]
            else role_data["name"],
        )
        for role_id, role_data in roles.items()
        if role_id != 0  # Исключаем роль "Не авторизован"
    ]

    # Получаем allowed_roles из БД
    allowed_roles = settings.allowed_roles if settings.allowed_roles else []

    # Устанавливаем выбранные роли в мультиселект
    access_level_select: ManagedMultiselect = dialog_manager.find("access_level_select")
    for role_id, _ in roles_list:
        is_allowed = role_id in allowed_roles
        await access_level_select.set_checked(str(role_id), is_allowed)

    allow_unemployed = dialog_manager.find("only_employees")
    await allow_unemployed.set_checked(settings.remove_unemployed)

    # Проверяем, есть ли неподходящие пользователи
    has_inappropriate_users = False
    try:
        inappropriate_data = await inappropriate_users_getter(
            stp_repo=stp_repo,
            bot=bot,
            dialog_manager=dialog_manager,
        )
        has_inappropriate_users = inappropriate_data["has_inappropriate_users"]
    except Exception:
        # Если не удалось получить данные, не показываем кнопку
        has_inappropriate_users = False

    return {
        "group_name": chat.title,
        "roles": roles_list,
        "has_pending_changes": False,
        "has_inappropriate_users": has_inappropriate_users,
    }


async def group_details_services_getter(
    stp_repo: MainRequestsRepo,
    bot: Bot,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict:
    """Геттер для окна настройки сервисных сообщений группы.

    Args:
        stp_repo: Репозиторий операций с базой STP
        bot: Экземпляр бота
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с данными для окна, включая список типов сервисных сообщений
    """
    group_id = dialog_manager.dialog_data["group_id"]

    try:
        chat = await bot.get_chat(chat_id=group_id)
    except (TelegramBadRequest, TelegramForbiddenError, TelegramAPIError) as e:
        return {
            "service_messages": [],
            "group_name": f"Группа недоступна (ID: {group_id})",
            "error": str(e),
        }

    settings = await stp_repo.group.get_groups(group_id=group_id)

    service_messages_items = [
        ("join", "Вход"),
        ("leave", "Выход"),
        ("other", "Прочее"),
        ("photo", "Фото"),
        ("pin", "Закреп"),
        ("title", "Название"),
        ("videochat", "Видеозвонки"),
    ]

    # Получаем service_messages из БД
    service_messages = settings.service_messages if settings.service_messages else []

    # Устанавливаем выбранные типы сообщений в мультиселект
    service_messages_select: ManagedMultiselect = dialog_manager.find(
        "service_messages_select"
    )
    for msg_type, _ in service_messages_items:
        is_selected = msg_type in service_messages
        await service_messages_select.set_checked(msg_type, is_selected)

    return {
        "service_messages": service_messages_items,
        "group_name": chat.title,
    }


async def group_remove_getter(
    dialog_manager: DialogManager, bot: Bot, **_kwargs
) -> dict:
    """Геттер для окна подтверждения удаления бота из группы.

    Args:
        dialog_manager: Менеджер диалога
        bot: Экземпляр бота

    Returns:
        Словарь с данными для окна
    """
    group_id = dialog_manager.dialog_data["group_id"]

    try:
        chat = await bot.get_chat(chat_id=group_id)
        group_name = chat.title
    except (TelegramBadRequest, TelegramForbiddenError, TelegramAPIError):
        group_name = f"ID: {group_id}"

    return {
        "group_name": group_name,
    }


async def inappropriate_users_getter(
    stp_repo: MainRequestsRepo,
    bot: Bot,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict:
    """Геттер для окна списка неподходящих пользователей группы.

    Определяет пользователей, которые не должны быть в группе согласно настройкам:
    - пользователи с неподходящими ролями (не входят в allowed_roles)
    - безработные пользователи (если remove_unemployed=True)

    Args:
        stp_repo: Репозиторий операций с базой STP
        bot: Экземпляр бота
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с данными неподходящих пользователей
    """
    group_id = dialog_manager.dialog_data["group_id"]

    try:
        chat = await bot.get_chat(chat_id=group_id)
    except (TelegramBadRequest, TelegramForbiddenError, TelegramAPIError) as e:
        return {
            "group_name": f"ID: {group_id}",
            "inappropriate_users": [],
            "has_inappropriate_users": False,
            "users_count": 0,
            "has_multiple_users": False,
            "error": str(e),
        }

    group_settings = await stp_repo.group.get_groups(group_id=group_id)

    # Получаем всех участников группы
    group_members = await stp_repo.group_member.get_group_members(group_id=group_id)

    inappropriate_users = []

    for member in group_members:
        # Получаем информацию о сотруднике
        try:
            employee = await stp_repo.employee.get_users(user_id=member.member_id)

            # Проверяем, является ли пользователь неподходящим
            is_inappropriate = False
            reason = []

            # Проверка по ролям
            if group_settings.allowed_roles:
                if employee.role not in group_settings.allowed_roles:
                    is_inappropriate = True
                    role_name = roles.get(employee.role, {}).get(
                        "name", "Неизвестная роль"
                    )
                    reason.append(f"роль: {role_name}")

            # Проверка по статусу трудоустройства
            if group_settings.remove_unemployed and not employee:
                is_inappropriate = True
                reason.append("уволен")

            if is_inappropriate:
                # Получаем информацию о пользователе Telegram
                try:
                    if employee:
                        display_name = format_fullname(employee, True, True)
                    else:
                        display_name = f"ID: {member.member_id}"
                except Exception:
                    display_name = f"ID: {member.member_id}"

                inappropriate_users.append({
                    "user_id": member.member_id,
                    "display_name": display_name,
                    "reason": ", ".join(reason),
                    "employee_name": employee.fullname if employee else "Неизвестный",
                })

        except Exception:
            # Если сотрудник не найден в БД, проверяем настройки группы
            is_inappropriate = False
            reason = []

            # Если включена настройка "только сотрудники", то пользователи не из БД неподходящие
            if group_settings.remove_unemployed:
                is_inappropriate = True
                reason.append("не найден в БД")

            # Если есть ограничения по ролям, то пользователи не из БД тоже неподходящие
            if group_settings.allowed_roles:
                is_inappropriate = True
                if "не найден в БД" not in reason:
                    reason.append("не найден в БД")

            if is_inappropriate:
                try:
                    telegram_user = await bot.get_chat_member(
                        chat_id=group_id, user_id=member.member_id
                    )
                    user_name = (
                        telegram_user.user.full_name or f"ID: {member.member_id}"
                    )
                    username = telegram_user.user.username
                    if username:
                        user_display = f"{user_name} (@{username})"
                    else:
                        user_display = user_name
                except (
                    TelegramBadRequest,
                    TelegramForbiddenError,
                    TelegramAPIError,
                    Exception,
                ):
                    user_display = f"ID: {member.member_id}"

                inappropriate_users.append({
                    "user_id": member.member_id,
                    "display_name": user_display,
                    "reason": ", ".join(reason),
                    "employee_name": "Неизвестный",
                })

    return {
        "group_name": chat.title,
        "inappropriate_users": [
            (user["display_name"], user["user_id"], user["reason"])
            for user in inappropriate_users
        ],
        "has_inappropriate_users": len(inappropriate_users) > 0,
        "users_count": len(inappropriate_users),
        "has_multiple_users": len(inappropriate_users) > 1,
    }

"""Геттеры для функционала управления группами."""

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.deep_linking import create_startgroup_link
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import ManagedCheckbox, ManagedMultiselect
from stp_database import Employee, MainRequestsRepo

from tgbot.misc.dicts import roles


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
        except TelegramBadRequest:
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
    group_id = (
        dialog_manager.dialog_data.get("group_id", None)
        or dialog_manager.start_data["group_id"]
    )

    chat = await bot.get_chat(chat_id=group_id)

    settings = await stp_repo.group.get_groups(group_id=group_id)

    # Установка флага инициализации для предотвращения обновления БД
    dialog_manager.dialog_data["initializing_checkboxes"] = True

    # Установка настроек из БД
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
    chat = await bot.get_chat(chat_id=group_id)
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

    return {
        "group_name": chat.title,
        "roles": roles_list,
        "has_pending_changes": False,
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
    chat = await bot.get_chat(chat_id=group_id)
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
    chat = await bot.get_chat(chat_id=group_id)

    return {
        "group_name": chat.title,
    }

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
from stp_database.models.STP import Employee
from stp_database.repo.STP import MainRequestsRepo

from tgbot.misc.dicts import roles
from tgbot.misc.helpers import get_role, short_name


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


async def groups_access_getter(
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
            "has_inappropriate_users": False,
            "error": str(e),
        }

    settings = await stp_repo.group.get_groups(group_id=group_id)

    allow_unemployed = dialog_manager.find("only_employees")
    await allow_unemployed.set_checked(settings.remove_unemployed)

    # Проверяем, есть ли неподходящие пользователи
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
        "has_inappropriate_users": has_inappropriate_users,
        "has_allowed_divisions": settings.allowed_divisions,
    }


async def groups_access_roles_getter(
    stp_repo: MainRequestsRepo,
    bot: Bot,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict:
    """Геттер для окна настройки ролей для доступа к группе.

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
    access_level_select: ManagedMultiselect = dialog_manager.find("access_role_select")
    for role_id, _ in roles_list:
        is_allowed = role_id in allowed_roles
        await access_level_select.set_checked(str(role_id), is_allowed)

    return {
        "group_name": chat.title,
        "roles": roles_list,
    }


async def settings_access_divisions_getter(
    stp_repo: MainRequestsRepo,
    bot: Bot,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict:
    """Геттер для окна настройки направлений для доступа в группе.

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
            "divisions": [],
            "error": str(e),
        }

    settings = await stp_repo.group.get_groups(group_id=group_id)

    # Создаем список подразделений с соответствующими эмодзи
    # Используем названия подразделений как ID для хранения в БД
    divisions_list = [
        ("НТП1", "📞 НТП1"),
        ("НТП2", "📞 НТП2"),
        ("НЦК", "💬 НЦК"),
    ]

    # Получаем allowed_divisions из БД (используем allowed_roles как временное решение если нет allowed_divisions)
    allowed_divisions = (
        getattr(settings, "allowed_divisions", [])
        if hasattr(settings, "allowed_divisions")
        else []
    )

    # Если нет поля allowed_divisions, создаем пустой список для начальной инициализации
    if not allowed_divisions:
        allowed_divisions = []

    # Устанавливаем выбранные подразделения в мультиселект
    access_division_select: ManagedMultiselect = dialog_manager.find(
        "access_division_select"
    )
    if access_division_select:
        for division_id, _ in divisions_list:
            is_allowed = division_id in allowed_divisions
            await access_division_select.set_checked(division_id, is_allowed)

    return {
        "group_name": chat.title,
        "divisions": divisions_list,
    }


async def settings_access_positions_getter(
    stp_repo: MainRequestsRepo,
    bot: Bot,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict:
    """Геттер для окна настройки должностей для доступа в группе.

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
            "positions": [],
            "error": str(e),
        }

    # Получаем fresh данные из БД (важно для корректной работы после обновлений)
    settings = await stp_repo.group.get_groups(group_id=group_id)

    # Получаем allowed_divisions из БД
    allowed_divisions = settings.allowed_divisions or []

    # Если нет allowed_divisions, возвращаем пустой список должностей
    if not allowed_divisions:
        allowed_positions = []
        positions_list = []
        dialog_manager.dialog_data["position_mapping"] = {}
    else:
        # Получаем всех сотрудников
        all_employees = await stp_repo.employee.get_users()

        # Фильтруем сотрудников по allowed_divisions и получаем уникальные должности
        positions_set = set()
        for employee in all_employees:
            if employee.division in allowed_divisions and employee.position:
                positions_set.add(employee.position)

        # Сортируем должности и создаем маппинг с короткими ID
        sorted_positions = sorted(positions_set)
        position_mapping = {}
        positions_list = []

        for i, position in enumerate(sorted_positions):
            short_id = f"pos_{i}"
            position_mapping[short_id] = position
            positions_list.append((short_id, position))

        # Сохраняем маппинг в dialog_data для использования в обработчиках
        dialog_manager.dialog_data["position_mapping"] = position_mapping

        # Получаем allowed_positions из БД
        allowed_positions = settings.allowed_positions or []

    # Устанавливаем выбранные должности в мультиселект
    access_position_select: ManagedMultiselect = dialog_manager.find(
        "access_position_select"
    )
    if access_position_select:
        for short_id, position_name in positions_list:
            is_allowed = position_name in allowed_positions
            await access_position_select.set_checked(short_id, is_allowed)

    # Сброс флага инициализации
    dialog_manager.dialog_data["initializing_checkboxes"] = False

    return {
        "group_name": chat.title,
        "positions": positions_list,
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


async def groups_members_getter(
    stp_repo: MainRequestsRepo,
    bot: Bot,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict:
    """Геттер для окна списка участников группы.

    Args:
        stp_repo: Репозиторий операций с базой STP
        bot: Экземпляр бота
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с данными участников группы
    """
    group_id = dialog_manager.dialog_data["group_id"]

    try:
        chat = await bot.get_chat(chat_id=group_id)
    except (TelegramBadRequest, TelegramForbiddenError, TelegramAPIError) as e:
        return {
            "group_name": f"ID: {group_id}",
            "members": [],
            "has_members": False,
            "members_count": 0,
            "error": str(e),
        }

    # Получаем всех участников группы
    group_members = await stp_repo.group_member.get_group_members(group_id=group_id)

    # Собираем информацию о всех участниках и их ролях
    members_list = []
    available_roles = set()

    for member in group_members:
        try:
            # Сначала проверяем, есть ли пользователь в базе сотрудников
            employee = await stp_repo.employee.get_users(user_id=member.member_id)

            if employee:
                # Если сотрудник найден, показываем его с ролевым эмодзи
                role_info = get_role(employee.role)
                role_emoji = role_info["emoji"] if role_info["emoji"] else "👤"
                display_name = f"{role_emoji} {short_name(employee.fullname)}"
                member_type = "employee"
                member_role = employee.role
                position = (
                    f"{employee.position} {employee.division}"
                    if employee.position and employee.division
                    else ""
                )
                # Добавляем роль в доступные фильтры
                available_roles.add(employee.role)
            else:
                # Если не сотрудник, получаем информацию из Telegram с дефолтным эмодзи
                try:
                    telegram_user = await bot.get_chat_member(
                        chat_id=group_id, user_id=member.member_id
                    )
                    user_name = (
                        telegram_user.user.full_name or f"ID: {member.member_id}"
                    )
                    if telegram_user.user.username:
                        user_name += f" (@{telegram_user.user.username})"
                    display_name = f"👤 {user_name}"
                    member_type = "user"
                    member_role = "unregistered"
                    position = "Не сотрудник"
                except (TelegramBadRequest, TelegramForbiddenError, TelegramAPIError):
                    display_name = f"👤 ID: {member.member_id}"
                    member_type = "user"
                    member_role = "unregistered"
                    position = "Неизвестный"

                # Добавляем "неавторизованных" в доступные фильтры
                available_roles.add("unregistered")

            members_list.append((
                display_name,
                str(member.member_id),
                member_type,
                position,
                member_role,
            ))

        except Exception:
            # Если что-то пошло не так, добавляем с минимальной информацией
            members_list.append((
                f"👤 ID: {member.member_id}",
                str(member.member_id),
                "user",
                "Ошибка",
                "unregistered",
            ))
            available_roles.add("unregistered")

    def get_sort_name(member_tuple):
        """Извлекает имя для сортировки, убирая эмодзи и символы."""
        display_name = member_tuple[0]
        # Убираем эмодзи и лишние символы для правильной сортировки
        import re

        # Убираем эмодзи в начале строки (до первого пробела)
        clean_name = re.sub(r"^[^\w\s]+\s*", "", display_name)
        # Убираем @ символы и другие спецсимволы
        clean_name = re.sub(r"[@()]+", "", clean_name)
        return clean_name.strip().lower()

    # Сортируем: сначала сотрудники, потом остальные, внутри каждой группы по имени (алфавитно)
    members_list.sort(key=lambda x: (x[2] != "employee", get_sort_name(x)))

    # Создаем список доступных фильтров по ролям
    role_filters = [("all", "Все")]

    # Добавляем фильтры для ролей сотрудников
    for role_id in sorted(available_roles):
        if role_id != "unregistered":
            role_info = get_role(role_id)
            role_name = (
                f"{role_info['emoji']} {role_info['name']}"
                if role_info["emoji"]
                else role_info["name"]
            )
            role_filters.append((str(role_id), role_name))

    # Добавляем фильтр для незарегистрированных, если они есть
    if "unregistered" in available_roles:
        role_filters.append(("unregistered", "👤 Незарегистрированные"))

    # Получаем текущий выбранный фильтр из dialog_data
    from aiogram_dialog.widgets.kbd import ManagedRadio

    try:
        role_filter_radio: ManagedRadio = dialog_manager.find("role_filter")
        current_filter = role_filter_radio.get_checked() or "all"
    except Exception:
        current_filter = "all"

    # Фильтруем участников по выбранной роли
    if current_filter == "all":
        filtered_members = [(m[0], m[1], m[2], m[3]) for m in members_list]
        current_filter_name = "Все"
    else:
        filtered_members = []
        current_filter_name = "Неизвестный фильтр"

        # Находим название текущего фильтра
        for filter_id, filter_name in role_filters:
            if filter_id == current_filter:
                current_filter_name = filter_name
                break

        # Фильтруем участников
        for member in members_list:
            member_role = member[4]  # роль находится на 5-й позиции
            if str(member_role) == current_filter:
                filtered_members.append((member[0], member[1], member[2], member[3]))

        # Сортируем отфильтрованных участников алфавитно
        filtered_members.sort(key=lambda x: get_sort_name(x))

    # Получаем тип группы для правильного отображения
    group_settings = await stp_repo.group.get_groups(group_id=group_id)
    group_type = "канала" if group_settings.group_type == "channel" else "группы"

    return {
        "group_name": chat.title,
        "group_type": group_type,
        "members": members_list,  # полный список для подсчета
        "filtered_members": filtered_members,  # отфильтрованный список для отображения
        "has_members": len(members_list) > 0,
        "members_count": len(members_list),
        "filtered_count": len(filtered_members),
        "available_role_filters": role_filters,
        "has_role_filters": len(role_filters)
        > 1,  # показываем фильтры только если есть больше одной опции
        "current_filter_name": current_filter_name,
    }


async def member_details_getter(
    stp_repo: MainRequestsRepo,
    bot: Bot,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict:
    """Геттер для окна детальной информации о участнике группы.

    Args:
        stp_repo: Репозиторий операций с базой STP
        bot: Экземпляр бота
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с детальной информацией об участнике
    """
    group_id = dialog_manager.dialog_data["group_id"]
    member_id = dialog_manager.dialog_data.get("selected_member_id")

    if not member_id:
        return {
            "error": "Не выбран участник для просмотра",
            "group_name": "Ошибка",
            "member_info": "Участник не найден",
            "is_employee": False,
            "can_kick": False,
        }

    try:
        chat = await bot.get_chat(chat_id=group_id)
        group_name = chat.title
    except (TelegramBadRequest, TelegramForbiddenError, TelegramAPIError):
        group_name = f"ID: {group_id}"

    try:
        # Проверяем, является ли администратором или создателем
        chat_admins = await bot.get_chat_administrators(chat_id=group_id)
        is_admin = any(admin.user.id == int(member_id) for admin in chat_admins)
        is_creator = any(
            admin.user.id == int(member_id) and admin.status == "creator"
            for admin in chat_admins
        )

        # Нельзя кикнуть администратора или создателя
        can_kick = not is_admin and not is_creator

    except (TelegramBadRequest, TelegramForbiddenError, TelegramAPIError):
        can_kick = True  # Если не можем проверить, разрешаем попробовать

    # Проверяем, есть ли пользователь в базе сотрудников
    employee = await stp_repo.employee.get_users(user_id=int(member_id))

    if employee:
        # Если сотрудник - используем функцию из whois.py
        from tgbot.handlers.groups.user.whois import create_user_info_message

        # Получаем информацию о руководителе, если указан
        user_head = None
        if employee.head:
            user_head = await stp_repo.employee.get_users(fullname=employee.head)

        member_info = create_user_info_message(employee, user_head)
        is_employee = True

    else:
        # Если не сотрудник - показываем базовую информацию из Telegram
        try:
            telegram_user = await bot.get_chat_member(
                chat_id=group_id, user_id=int(member_id)
            )
            user = telegram_user.user

            member_info = f"<b>{user.full_name or 'Неизвестное имя'}</b>\n\n"

            if user.username:
                member_info += f"<b>👤 Username:</b> @{user.username}\n"

            member_info += f"<b>🆔 ID:</b> <code>{user.id}</code>\n"
            member_info += (
                f"<b>🤖 Тип:</b> {'Бот' if user.is_bot else 'Пользователь'}\n"
            )

            # Информация о статусе в группе
            if telegram_user.status == "administrator":
                member_info += "<b>🛡️ Статус:</b> Администратор\n"
            elif telegram_user.status == "creator":
                member_info += "<b>👑 Статус:</b> Создатель\n"
            else:
                member_info += "<b>👤 Статус:</b> Участник\n"

        except (TelegramBadRequest, TelegramForbiddenError, TelegramAPIError):
            member_info = f"<b>ID: {member_id}</b>\n\nИнформация недоступна"

        is_employee = False

    return {
        "group_name": group_name,
        "member_info": member_info,
        "is_employee": is_employee,
        "can_kick": can_kick,
        "member_id": member_id,
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

    # Получаем создателя группы/канала
    creator_id = None
    try:
        chat_admins = await bot.get_chat_administrators(chat_id=group_id)
        for admin in chat_admins:
            if admin.status == "creator":
                creator_id = admin.user.id
                break
    except (TelegramBadRequest, TelegramForbiddenError, TelegramAPIError):
        # Если не можем получить администраторов, продолжаем без фильтрации создателя
        pass

    inappropriate_users = []

    for member in group_members:
        # Пропускаем создателя группы/канала, так как его нельзя исключить
        if creator_id and member.member_id == creator_id:
            continue

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
                        display_name = short_name(employee.fullname)
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

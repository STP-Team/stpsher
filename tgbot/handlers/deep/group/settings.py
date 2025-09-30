import logging

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.utils.payload import decode_payload

from infrastructure.database.models.STP.group import Group
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.deep import DeepLinkRegexFilter
from tgbot.keyboards.group.main import (
    GroupAccessApplyMenu,
    GroupAccessMenu,
    GroupMemberActionMenu,
    GroupMemberDetailMenu,
    GroupMembersMenu,
    GroupServiceMessagesApplyMenu,
    GroupServiceMessagesMenu,
    GroupSettingsMenu,
    group_access_kb,
    group_member_detail_kb,
    group_members_kb,
    group_service_messages_kb,
    group_settings_kb,
)
from tgbot.misc.dicts import roles

deeplink_group = Router()
logger = logging.getLogger(__name__)

# Store pending role changes per group
pending_role_changes = {}
# Store pending service messages changes per group
pending_service_messages_changes = {}


@deeplink_group.message(
    CommandStart(deep_link=True), DeepLinkRegexFilter(r"^group_-?\d+$")
)
async def handle_settings(
    message: Message, command: CommandObject, stp_repo: MainRequestsRepo
):
    """Redirect to groups management menu with specific group selected."""
    from tgbot.handlers.group.management import (
        check_user_admin_status,
        get_user_groups,
    )
    from tgbot.keyboards.group.main import group_management_kb, group_settings_kb

    payload = decode_payload(command.args)
    group_id = int(payload.split("_", 1)[1])
    user_id = message.from_user.id

    try:
        # Check if user is in the group
        user_groups, admin_status = await get_user_groups(
            user_id, stp_repo, message.bot
        )
        group_found = any(gid == group_id for gid, _ in user_groups)

        if not group_found:
            await message.answer(
                """❌ <b>Группа недоступна</b>

Ты не состоишь в этой группе или она была удалена.

Для доступа к настройкам группы тебе необходимо:
1. Состоять в группе
2. Чтобы изменять настройки - иметь права администратора"""
            )
            return

        # Get group info
        group = await stp_repo.group.get_group(group_id)
        if not group:
            await message.answer("❌ Группа не найдена в базе данных")
            return

        # Check admin status
        is_admin = await check_user_admin_status(user_id, group_id, message.bot)

        chat_info = await message.bot.get_chat(chat_id=group_id)
        group_name = chat_info.title or f"{group_id}"

        if is_admin:
            # Show full settings for admin
            await message.answer(
                f"""⚙️ <b>Настройки группы</b>: {group_name}

<b>Обозначения</b>
- 🟢 Опция включена
- 🔴 Опция выключена

<i>Используй меню для управления функциями бота в группе</i>

💡 <b>Совет:</b> Теперь все настройки групп доступны через основное меню бота в разделе "Группы"!""",
                reply_markup=group_settings_kb(group, 1),
            )
        else:
            # Show info for regular user
            await message.answer(
                f"""📄 <b>Информация о группе</b>: {group_name}

<b>Текущие настройки</b>:
{"🟢" if group.remove_unemployed else "🔴"} Только сотрудники
{"🟢" if group.new_user_notify else "🔴"} Приветствие новых участников
{"🟢" if group.is_casino_allowed else "🔴"} Казино

🛡️ <b>Доступ к группе</b>: {"Настроен" if group.allowed_roles else "Открыт для всех"}

🗑️ <b>Сервисные сообщения</b>: {"Настроено" if hasattr(group, "service_messages") and group.service_messages else "Не настроено"}

<i>Для изменения настроек необходимо иметь права администратора в группе</i>""",
                reply_markup=group_management_kb(user_groups, 1),
            )

    except Exception as e:
        logger.error(f"Error handling deep link for group {group_id}: {e}")
        await message.answer(
            """❌ <b>Ошибка доступа</b>

Произошла ошибка при доступе к настройкам группы.

💡 <b>Попробуй:</b> Открой основное меню бота → "Группы" → "Управление группами" """
        )


async def _update_toggle_setting(
    callback: CallbackQuery,
    stp_repo: MainRequestsRepo,
    group: Group,
    field_name: str,
    current_value: bool,
    success_message: str,
) -> None:
    """Helper function to update toggle settings efficiently."""
    new_value = not current_value
    update_data = {field_name: new_value}

    logger.info(
        f"Updating group {group.group_id}: {field_name} from {current_value} to {new_value}"
    )

    updated_group = await stp_repo.group.update_group(
        group_id=group.group_id, **update_data
    )

    if updated_group:
        status = "включено" if new_value else "выключено"
        await callback.answer(f"{success_message} {status}")

        await callback.message.edit_reply_markup(
            reply_markup=group_settings_kb(updated_group, 1)
        )
        logger.info(f"Successfully updated group {group.group_id} setting {field_name}")
    else:
        await callback.answer("Ошибка при обновлении настройки")
        logger.error(f"Failed to update group {group.group_id} setting {field_name}")


@deeplink_group.callback_query(GroupSettingsMenu.filter())
async def handle_settings_callback(
    callback: CallbackQuery,
    callback_data: GroupSettingsMenu,
    stp_repo: MainRequestsRepo,
):
    group = await stp_repo.group.get_group(callback_data.group_id)
    if not group:
        await callback.answer("Не удалось найти группу в базе :(")
        return

    match callback_data.menu:
        case "remove_unemployed":
            await _update_toggle_setting(
                callback,
                stp_repo,
                group,
                "remove_unemployed",
                group.remove_unemployed,
                "Проверка регистрации",
            )

        case "is_casino_allowed":
            await _update_toggle_setting(
                callback,
                stp_repo,
                group,
                "is_casino_allowed",
                group.is_casino_allowed,
                "Казино",
            )

        case "new_user_notify":
            await _update_toggle_setting(
                callback,
                stp_repo,
                group,
                "new_user_notify",
                group.new_user_notify,
                "Приветствие новых участников",
            )

        case "access":
            # Initialize pending changes with current dialogs
            pending_role_changes[group.group_id] = (group.allowed_roles or []).copy()

            await callback.message.edit_text(
                """🛡️ <b>Уровень доступа к группе</b>

<b>Обозначения</b>
- 🟢 Имеет доступ
- 🔴 Не имеет доступа

<i>Выбери роли, которые должны иметь доступ к группе, затем нажми "Применить"</i>
<i>Если выключить все роли - у любого сотрудника будет доступ</i>

<blockquote expandable>Настройка не зависит от опции "Только сотрудники"

Если опция "Только сотрудники" отключена, и указаны уровни доступа, то:
- В группе смогут находиться не сотрудники
- В группу смогут попасть сотрудники только с указанными правами</blockquote>""",
                reply_markup=group_access_kb(
                    group, pending_role_changes[group.group_id], 1
                ),
            )

        case "members":
            # Get all group members from the database
            group_members = await stp_repo.group_member.get_group_members(
                group.group_id
            )

            # Get employee data for members who are employees
            employees = []
            non_employee_users = []

            for group_member in group_members:
                # Try to get employee data
                employee = await stp_repo.employee.get_user(
                    user_id=group_member.member_id
                )
                if employee:
                    employees.append(employee)
                else:
                    # Get user info from Telegram
                    try:
                        chat_member = await callback.bot.get_chat_member(
                            chat_id=group.group_id, user_id=group_member.member_id
                        )
                        non_employee_users.append(chat_member.user)
                    except Exception:
                        # User might have left the group or blocked the bot
                        continue

            total_members = len(employees) + len(non_employee_users)

            # Create role legend from dialogs dict
            role_legend = []
            for role_id, role_info in roles.items():
                if role_id not in [0, 10]:  # Skip unauthorized and root
                    role_legend.append(f"{role_info['emoji']} - {role_info['name']}")

            await callback.message.edit_text(
                f"""👥 <b>Состав группы</b>

Участники группы: <b>{total_members}</b>

<blockquote><b>Обозначения</b>
{chr(10).join(role_legend)}
@username (user_id) - обычные пользователи</blockquote>

<i>Нажми на участника для управления</i>""",
                reply_markup=group_members_kb(
                    group_id=group.group_id,
                    employees=employees,
                    users=non_employee_users,
                    current_page=1,
                ),
            )

        case "service_messages":
            # Initialize pending changes with current service messages categories
            pending_service_messages_changes[group.group_id] = (
                getattr(group, "service_messages", []) or []
            ).copy()

            await callback.message.edit_text(
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

<i>Выбери типы сообщений для удаления, затем нажми "Применить"</i>""",
                reply_markup=group_service_messages_kb(
                    group, pending_service_messages_changes[group.group_id], 1
                ),
            )

        case "back":
            group_info = await callback.bot.get_chat(chat_id=group.group_id)

            await callback.message.edit_text(
                f"""⚙️ <b>Настройки группы</b>: {group_info.full_name}

<b>Обозначения</b>
- 🟢 Опция включена
- 🔴 Опция выключена

<i>Используй меню для управления функциями бота в группе</i>""",
                reply_markup=group_settings_kb(group, 1),
            )


@deeplink_group.callback_query(GroupAccessMenu.filter())
async def handle_access_callback(
    callback: CallbackQuery,
    callback_data: GroupAccessMenu,
    stp_repo: MainRequestsRepo,
):
    group = await stp_repo.group.get_group(callback_data.group_id)
    if not group:
        await callback.answer("Не удалось найти группу в базе :(")
        return

    # Get current pending dialogs for this group
    if group.group_id not in pending_role_changes:
        pending_role_changes[group.group_id] = (group.allowed_roles or []).copy()

    current_pending = pending_role_changes[group.group_id]
    role_id = callback_data.role_id

    if role_id in current_pending:
        # Remove role from pending list
        pending_role_changes[group.group_id] = [
            r for r in current_pending if r != role_id
        ]
        action = "убрана из выбранных"
    else:
        # Add role to pending list
        pending_role_changes[group.group_id] = current_pending + [role_id]
        action = "добавлена к выбранным"

    from tgbot.misc.dicts import roles

    role_name = roles[role_id]["name"]
    await callback.answer(f"Роль '{role_name}' {action}")

    # Update keyboard with pending changes
    await callback.message.edit_reply_markup(
        reply_markup=group_access_kb(group, pending_role_changes[group.group_id], 1)
    )


@deeplink_group.callback_query(GroupAccessApplyMenu.filter())
async def handle_access_apply_callback(
    callback: CallbackQuery,
    callback_data: GroupAccessApplyMenu,
    stp_repo: MainRequestsRepo,
):
    group = await stp_repo.group.get_group(callback_data.group_id)
    if not group:
        await callback.answer("Не удалось найти группу в базе :(")
        return

    if callback_data.action == "apply":
        # Apply the pending changes
        if group.group_id in pending_role_changes:
            new_roles = pending_role_changes[group.group_id]

            updated_group = await stp_repo.group.update_group(
                group_id=group.group_id, allowed_roles=new_roles
            )

            if updated_group:
                await callback.answer("✅ Настройки доступа применены!")

                # Clean up pending changes
                del pending_role_changes[group.group_id]

                # Update keyboard without pending changes
                await callback.message.edit_reply_markup(
                    reply_markup=group_access_kb(updated_group, page=1)
                )
                logger.info(
                    f"Successfully applied access roles for group {group.group_id}"
                )
            else:
                await callback.answer("❌ Ошибка при применении настроек")
                logger.error(f"Failed to apply access roles for group {group.group_id}")
        else:
            await callback.answer("Нет изменений для применения")

    elif callback_data.action == "cancel":
        # Cancel pending changes
        if group.group_id in pending_role_changes:
            del pending_role_changes[group.group_id]

        await callback.answer("❌ Изменения отменены")

        # Update keyboard with original dialogs
        await callback.message.edit_reply_markup(
            reply_markup=group_access_kb(group, page=1)
        )


@deeplink_group.callback_query(GroupMembersMenu.filter())
async def handle_members_pagination(
    callback: CallbackQuery,
    callback_data: GroupMembersMenu,
    stp_repo: MainRequestsRepo,
):
    """Handle members list pagination"""
    group = await stp_repo.group.get_group(callback_data.group_id)
    if not group:
        await callback.answer("Не удалось найти группу в базе :(")
        return

    # Get all group members from the database
    group_members = await stp_repo.group_member.get_group_members(group.group_id)

    # Get employee data for members who are employees
    employees = []
    non_employee_users = []

    for group_member in group_members:
        # Try to get employee data
        employee = await stp_repo.employee.get_user(user_id=group_member.member_id)
        if employee:
            employees.append(employee)
        else:
            # Get user info from Telegram
            try:
                chat_member = await callback.bot.get_chat_member(
                    chat_id=group.group_id, user_id=group_member.member_id
                )
                non_employee_users.append(chat_member.user)
            except Exception:
                # User might have left the group or blocked the bot
                continue

    total_members = len(employees) + len(non_employee_users)

    # Create role legend from dialogs dict
    role_legend = []
    for role_id, role_info in roles.items():
        if role_id not in [0, 10]:  # Skip unauthorized and root
            role_legend.append(f"{role_info['emoji']} - {role_info['name']}")

    await callback.message.edit_text(
        f"""👥 <b>Состав группы</b>

Участники группы: <b>{total_members}</b>

<blockquote><b>Обозначения</b>
{chr(10).join(role_legend)}
@username (user_id) - обычные пользователи</blockquote>

<i>Нажми на участника для управления</i>""",
        reply_markup=group_members_kb(
            group_id=group.group_id,
            employees=employees,
            users=non_employee_users,
            current_page=callback_data.page,
        ),
    )


@deeplink_group.callback_query(GroupMemberDetailMenu.filter())
async def handle_member_detail(
    callback: CallbackQuery,
    callback_data: GroupMemberDetailMenu,
    stp_repo: MainRequestsRepo,
):
    """Handle member detail view"""
    group = await stp_repo.group.get_group(callback_data.group_id)
    if not group:
        await callback.answer("Не удалось найти группу в базе :(")
        return

    if callback_data.member_type == "employee":
        # Get employee data
        employee = await stp_repo.employee.get_user(user_id=callback_data.member_id)
        if employee:
            from tgbot.keyboards.group.main import short_name

            member_name = short_name(employee.fullname)
            role_info = roles.get(
                employee.role, {"name": "Неизвестная роль", "emoji": ""}
            )
            member_info = f"""👤 <b>Сотрудник</b>: {employee.fullname}
🏷️ <b>Роль</b>: {role_info["emoji"]} {role_info["name"]}
🆔 <b>ID</b>: <code>{employee.user_id}</code>"""
        else:
            await callback.answer("Не удалось найти данные сотрудника")
            return
    else:
        # Get user info from Telegram
        try:
            chat_member = await callback.bot.get_chat_member(
                chat_id=group.group_id, user_id=callback_data.member_id
            )
            user = chat_member.user
            username = f"@{user.username}" if user.username else "Нет username"
            full_name = f"{user.first_name}"
            if user.last_name:
                full_name += f" {user.last_name}"

            member_name = username
            member_info = f"""👤 <b>Пользователь</b>: {full_name}
👤 <b>Username</b>: {username}
🆔 <b>ID</b>: <code>{user.id}</code>"""
        except Exception:
            await callback.answer("Не удалось получить информацию о пользователе")
            return

    await callback.message.edit_text(
        f"""🔍 <b>Детали участника</b>

{member_info}

<i>Выбери действие для управления участником</i>""",
        reply_markup=group_member_detail_kb(
            group_id=callback_data.group_id,
            member_id=callback_data.member_id,
            member_type=callback_data.member_type,
            member_name=member_name,
            page=callback_data.page,
        ),
    )


@deeplink_group.callback_query(GroupMemberActionMenu.filter())
async def handle_member_action(
    callback: CallbackQuery,
    callback_data: GroupMemberActionMenu,
    stp_repo: MainRequestsRepo,
):
    """Handle member actions (ban)"""
    group = await stp_repo.group.get_group(callback_data.group_id)
    if not group:
        await callback.answer("Не удалось найти группу в базе :(")
        return

    if callback_data.action == "ban":
        try:
            # Ban user from the group
            await callback.bot.ban_chat_member(
                chat_id=group.group_id, user_id=callback_data.member_id
            )

            # Remove from group_members table
            removal_success = await stp_repo.group_member.remove_member(
                group_id=group.group_id, member_id=callback_data.member_id
            )

            if removal_success:
                await callback.answer("✅ Участник забанен и удален из базы")
                logger.info(
                    f"User {callback_data.member_id} banned from group {group.group_id} "
                    f"and removed from database"
                )
            else:
                await callback.answer("⚠️ Участник забанен, но не удален из базы")
                logger.warning(
                    f"User {callback_data.member_id} banned from group {group.group_id} "
                    f"but failed to remove from database"
                )

            # Return to members list
            # Get updated members list
            group_members = await stp_repo.group_member.get_group_members(
                group.group_id
            )

            employees = []
            non_employee_users = []

            for group_member in group_members:
                employee = await stp_repo.employee.get_user(
                    user_id=group_member.member_id
                )
                if employee:
                    employees.append(employee)
                else:
                    try:
                        chat_member = await callback.bot.get_chat_member(
                            chat_id=group.group_id, user_id=group_member.member_id
                        )
                        non_employee_users.append(chat_member.user)
                    except Exception:
                        continue

            total_members = len(employees) + len(non_employee_users)

            # Create role legend
            role_legend = []
            for role_id, role_info in roles.items():
                if role_id not in [0, 10]:
                    role_legend.append(f"{role_info['emoji']} - {role_info['name']}")

            await callback.message.edit_text(
                f"""👥 <b>Состав группы</b>

Участники группы: <b>{total_members}</b>

<blockquote><b>Обозначения</b>
{chr(10).join(role_legend)}
@username (user_id) - обычные пользователи</blockquote>

<i>Нажми на участника для управления</i>""",
                reply_markup=group_members_kb(
                    group_id=group.group_id,
                    employees=employees,
                    users=non_employee_users,
                    current_page=callback_data.page,
                ),
            )

        except Exception as e:
            await callback.answer("❌ Ошибка при бане участника")
            logger.error(f"Failed to ban user {callback_data.member_id}: {e}")


@deeplink_group.callback_query(GroupServiceMessagesMenu.filter())
async def handle_service_messages_callback(
    callback: CallbackQuery,
    callback_data: GroupServiceMessagesMenu,
    stp_repo: MainRequestsRepo,
):
    group = await stp_repo.group.get_group(callback_data.group_id)
    if not group:
        await callback.answer("Не удалось найти группу в базе :(")
        return

    # Get current pending categories for this group
    if group.group_id not in pending_service_messages_changes:
        pending_service_messages_changes[group.group_id] = (
            getattr(group, "service_messages", []) or []
        ).copy()

    current_pending = pending_service_messages_changes[group.group_id]
    category = callback_data.category

    if category in current_pending:
        # Remove category from pending list
        pending_service_messages_changes[group.group_id] = [
            c for c in current_pending if c != category
        ]
        action = "убрана из удаляемых"
    else:
        # Add category to pending list
        pending_service_messages_changes[group.group_id] = current_pending + [category]
        action = "добавлена к удаляемым"

    # Category names for user feedback
    category_names = {
        "all": "Все сообщения",
        "join": "Вход пользователей",
        "leave": "Выход пользователей",
        "other": "Прочие сообщения",
        "photo": "Смена фото",
        "pin": "Закрепленные сообщения",
        "title": "Смена названия",
        "videochat": "Видеозвонки",
    }

    category_name = category_names.get(category, category)
    await callback.answer(f"Категория '{category_name}' {action}")

    # Update keyboard with pending changes
    await callback.message.edit_reply_markup(
        reply_markup=group_service_messages_kb(
            group, pending_service_messages_changes[group.group_id], 1
        )
    )


@deeplink_group.callback_query(GroupServiceMessagesApplyMenu.filter())
async def handle_service_messages_apply_callback(
    callback: CallbackQuery,
    callback_data: GroupServiceMessagesApplyMenu,
    stp_repo: MainRequestsRepo,
):
    group = await stp_repo.group.get_group(callback_data.group_id)
    if not group:
        await callback.answer("Не удалось найти группу в базе :(")
        return

    if callback_data.action == "apply":
        # Apply the pending changes
        if group.group_id in pending_service_messages_changes:
            new_categories = pending_service_messages_changes[group.group_id]

            updated_group = await stp_repo.group.update_group(
                group_id=group.group_id, service_messages=new_categories
            )

            if updated_group:
                await callback.answer("✅ Настройки сервисных сообщений применены!")

                # Clean up pending changes
                del pending_service_messages_changes[group.group_id]

                # Update keyboard without pending changes
                await callback.message.edit_reply_markup(
                    reply_markup=group_service_messages_kb(updated_group, page=1)
                )
                logger.info(
                    f"Successfully applied service messages settings for group {group.group_id}"
                )
            else:
                await callback.answer("❌ Ошибка при применении настроек")
                logger.error(
                    f"Failed to apply service messages settings for group {group.group_id}"
                )
        else:
            await callback.answer("Нет изменений для применения")

    elif callback_data.action == "cancel":
        # Cancel pending changes
        if group.group_id in pending_service_messages_changes:
            del pending_service_messages_changes[group.group_id]

        await callback.answer("❌ Изменения отменены")

        # Update keyboard with original categories
        await callback.message.edit_reply_markup(
            reply_markup=group_service_messages_kb(group, page=1)
        )

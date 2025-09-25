import logging
from typing import List, Tuple

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.keyboards.group.main import (
    GroupAccessApplyMenu,
    GroupAccessMenu,
    GroupManagementMenu,
    GroupMemberActionMenu,
    GroupMemberDetailMenu,
    GroupMembersMenu,
    GroupServiceMessagesApplyMenu,
    GroupServiceMessagesMenu,
    GroupSettingsMenu,
    GroupsMenu,
    group_access_kb,
    group_management_kb,
    group_member_detail_kb,
    group_members_kb,
    group_service_messages_kb,
    group_settings_kb,
)
from tgbot.misc.dicts import roles

logger = logging.getLogger(__name__)

group_management_router = Router()
group_management_router.callback_query.filter(F.message.chat.type == "private")

# Store pending role changes per group
pending_role_changes = {}
# Store pending service messages changes per group
pending_service_messages_changes = {}


async def get_user_groups(
    user_id: int, stp_repo: MainRequestsRepo, bot
) -> List[Tuple[int, str]]:
    """Get list of all groups where user is a member."""
    user_groups = []
    member_groups = await stp_repo.group_member.get_member_groups(user_id)

    for group_member in member_groups:
        group_id = group_member.group_id
        try:
            try:
                chat_info = await bot.get_chat(chat_id=group_id)
                group_name = chat_info.title or f"{group_id}"
                user_groups.append((group_id, group_name))
            except Exception as e:
                logger.warning(f"Failed to get chat info for group {group_id}: {e}")
                user_groups.append((group_id, f"{group_id}"))
        except Exception as e:
            logger.warning(f"Failed to check group {group_id}: {e}")
            continue

    return user_groups


async def check_user_admin_status(user_id: int, group_id: int, bot) -> bool:
    """Check if user is an admin of the group."""
    try:
        member_status = await bot.get_chat_member(chat_id=group_id, user_id=user_id)
        return member_status.status in ["administrator", "creator"]
    except Exception as e:
        logger.warning(f"Failed to check admin status for group {group_id}: {e}")
        return False


async def _update_toggle_setting(
    callback: CallbackQuery,
    stp_repo: MainRequestsRepo,
    group,
    field_name: str,
    current_value: bool,
    success_message: str,
    page: int = 1,
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
            reply_markup=group_settings_kb(updated_group, page)
        )
        logger.info(f"Successfully updated group {group.group_id} setting {field_name}")
    else:
        await callback.answer("Ошибка при обновлении настройки")
        logger.error(f"Failed to update group {group.group_id} setting {field_name}")


# =========================== MAIN HANDLERS ===========================


@group_management_router.callback_query(GroupsMenu.filter(F.menu == "management"))
async def handle_management_menu(callback: CallbackQuery, stp_repo: MainRequestsRepo):
    """Handle groups management menu."""
    user_id = callback.from_user.id
    user_groups = await get_user_groups(user_id, stp_repo, callback.bot)

    if not user_groups:
        await callback.message.edit_text(
            """🛡️ <b>Управление группами</b>

❌ <b>Ты не состоишь ни в одной группе</b>

Чтобы управлять настройками бота в группе, тебе необходимо:
1. Вступить в группу, где добавлен бот
2. Чтобы изменять настройки - получить права администратора

<i>После добавления в группу, вернись в это меню</i>""",
            reply_markup=group_management_kb([]),
        )
    else:
        await callback.message.edit_text(
            f"""🛡️ <b>Управление группами</b>

Найдено групп: <b>{len(user_groups)}</b>

<i>Выбери группу для просмотра настроек:</i>""",
            reply_markup=group_management_kb(user_groups),
        )

    await callback.answer()


@group_management_router.callback_query(GroupManagementMenu.filter(F.action == "page"))
async def handle_management_pagination(
    callback: CallbackQuery,
    callback_data: GroupManagementMenu,
    stp_repo: MainRequestsRepo,
):
    """Handle pagination in groups management menu."""
    user_id = callback.from_user.id
    user_groups = await get_user_groups(user_id, stp_repo, callback.bot)

    if not user_groups:
        await callback.answer("У тебя нет групп для управления")
        return

    await callback.message.edit_text(
        f"""🛡️ <b>Управление группами</b>

Найдено групп: <b>{len(user_groups)}</b>

<i>Выбери группу для просмотра настроек:</i>""",
        reply_markup=group_management_kb(user_groups, callback_data.page),
    )

    await callback.answer()


@group_management_router.callback_query(
    GroupManagementMenu.filter(F.action == "select_group")
)
async def handle_group_selection(
    callback: CallbackQuery,
    callback_data: GroupManagementMenu,
    stp_repo: MainRequestsRepo,
):
    """Handle group selection for management."""
    user_id = callback.from_user.id
    group_id = callback_data.group_id

    try:
        group = await stp_repo.group.get_group(group_id)
        if not group:
            await callback.answer("❌ Группа не найдена в базе данных")
            return

        is_admin = await check_user_admin_status(user_id, group_id, callback.bot)
        chat_info = await callback.bot.get_chat(chat_id=group_id)
        group_name = chat_info.title or f"{group_id}"

        if is_admin:
            await callback.message.edit_text(
                f"""⚙️ <b>Настройки группы</b>: {group_name}

<b>Обозначения</b>
- 🟢 Опция включена
- 🔴 Опция выключена

<i>Используй меню для управления функциями бота в группе</i>""",
                reply_markup=group_settings_kb(group, callback_data.page),
            )
        else:
            await callback.message.edit_text(
                f"""📄 <b>Информация о группе</b>: {group_name}

<b>Текущие настройки</b>:
{"🟢" if group.remove_unemployed else "🔴"} Только сотрудники
{"🟢" if group.new_user_notify else "🔴"} Приветствие новых участников
{"🟢" if group.is_casino_allowed else "🔴"} Казино

🛡️ <b>Доступ к группе</b>: {"Настроен" if group.allowed_roles else "Открыт для всех"}

🗑️ <b>Сервисные сообщения</b>: {"Настроено" if hasattr(group, "service_messages") and group.service_messages else "Не настроено"}

❗ <b>Чтобы изменять настройки, получи права администратора в группе</b>""",
                reply_markup=group_management_kb(
                    await get_user_groups(user_id, stp_repo, callback.bot),
                    callback_data.page,
                ),
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error handling group selection for group {group_id}: {e}")
        await callback.answer("❌ Ошибка при обработке запроса")


@group_management_router.callback_query(
    GroupManagementMenu.filter(F.action == "back_to_list")
)
async def handle_back_to_list(
    callback: CallbackQuery,
    callback_data: GroupManagementMenu,
    stp_repo: MainRequestsRepo,
):
    """Handle back to groups list."""
    user_id = callback.from_user.id
    user_groups = await get_user_groups(user_id, stp_repo, callback.bot)

    if not user_groups:
        await callback.message.edit_text(
            """🛡️ <b>Управление группами</b>

❌ <b>Ты не состоишь ни в одной группе</b>

Чтобы управлять настройками бота в группе, тебе необходимо:
1. Вступить в группу, где добавлен бот
2. Чтобы изменять настройки - получить права администратора

<i>После добавления в группу, вернись в это меню</i>""",
            reply_markup=group_management_kb([]),
        )
    else:
        await callback.message.edit_text(
            f"""🛡️ <b>Управление группами</b>

Найдено групп: <b>{len(user_groups)}</b>

<i>Выбери группу для просмотра настроек:</i>""",
            reply_markup=group_management_kb(user_groups, callback_data.page),
        )

    await callback.answer()


# =========================== SETTINGS HANDLERS ===========================


@group_management_router.callback_query(GroupSettingsMenu.filter())
async def handle_settings_callback(
    callback: CallbackQuery,
    callback_data: GroupSettingsMenu,
    stp_repo: MainRequestsRepo,
):
    """Handle group settings."""
    user_id = callback.from_user.id
    group_id = callback_data.group_id

    if not await check_user_admin_status(user_id, group_id, callback.bot):
        await callback.answer("❌ У тебя нет прав администратора в этой группе")
        return

    group = await stp_repo.group.get_group(group_id)
    if not group:
        await callback.answer("❌ Группа не найдена в базе данных")
        return

    match callback_data.menu:
        case "remove_unemployed" | "is_casino_allowed" | "new_user_notify":
            field_name = callback_data.menu
            current_value = getattr(group, field_name)

            success_messages = {
                "remove_unemployed": "Только сотрудники",
                "is_casino_allowed": "Казино",
                "new_user_notify": "Приветствие новых участников",
            }

            await _update_toggle_setting(
                callback,
                stp_repo,
                group,
                field_name,
                current_value,
                success_messages[field_name],
                callback_data.page,
            )

        case "access":
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
                    group, pending_role_changes[group.group_id], callback_data.page
                ),
            )

        case "service_messages":
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
                    group,
                    pending_service_messages_changes[group.group_id],
                    callback_data.page,
                ),
            )

        case "members":
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
                    current_page=1,
                    list_page=callback_data.page,
                ),
            )

        case "back":
            chat_info = await callback.bot.get_chat(chat_id=group.group_id)
            group_name = chat_info.title or f"{group_id}"

            await callback.message.edit_text(
                f"""⚙️ <b>Настройки группы</b>: {group_name}

<b>Обозначения</b>
- 🟢 Опция включена
- 🔴 Опция выключена

<i>Используй меню для управления функциями бота в группе</i>""",
                reply_markup=group_settings_kb(group, callback_data.page),
            )

    await callback.answer()


# =========================== ACCESS CONTROL HANDLERS ===========================


@group_management_router.callback_query(GroupAccessMenu.filter())
async def handle_access_callback(
    callback: CallbackQuery,
    callback_data: GroupAccessMenu,
    stp_repo: MainRequestsRepo,
):
    """Handle access control settings."""
    user_id = callback.from_user.id
    group_id = callback_data.group_id

    if not await check_user_admin_status(user_id, group_id, callback.bot):
        await callback.answer("❌ У тебя нет прав администратора в этой группе")
        return

    group = await stp_repo.group.get_group(group_id)
    if not group:
        await callback.answer("❌ Группа не найдена в базе данных")
        return

    if group.group_id not in pending_role_changes:
        pending_role_changes[group.group_id] = (group.allowed_roles or []).copy()

    current_pending = pending_role_changes[group.group_id]
    role_id = callback_data.role_id

    if role_id in current_pending:
        pending_role_changes[group.group_id] = [
            r for r in current_pending if r != role_id
        ]
        action = "убрана из выбранных"
    else:
        pending_role_changes[group.group_id] = current_pending + [role_id]
        action = "добавлена к выбранным"

    role_name = roles[role_id]["name"]
    await callback.answer(f"Роль '{role_name}' {action}")

    await callback.message.edit_reply_markup(
        reply_markup=group_access_kb(
            group, pending_role_changes[group.group_id], callback_data.page
        )
    )


@group_management_router.callback_query(GroupAccessApplyMenu.filter())
async def handle_access_apply_callback(
    callback: CallbackQuery,
    callback_data: GroupAccessApplyMenu,
    stp_repo: MainRequestsRepo,
):
    """Handle access control apply/cancel."""
    user_id = callback.from_user.id
    group_id = callback_data.group_id

    if not await check_user_admin_status(user_id, group_id, callback.bot):
        await callback.answer("❌ У тебя нет прав администратора в этой группе")
        return

    group = await stp_repo.group.get_group(group_id)
    if not group:
        await callback.answer("❌ Группа не найдена в базе данных")
        return

    if callback_data.action == "apply":
        if group.group_id in pending_role_changes:
            new_roles = pending_role_changes[group.group_id]

            updated_group = await stp_repo.group.update_group(
                group_id=group.group_id, allowed_roles=new_roles
            )

            if updated_group:
                await callback.answer("✅ Настройки доступа применены!")
                del pending_role_changes[group.group_id]

                await callback.message.edit_reply_markup(
                    reply_markup=group_access_kb(updated_group, page=callback_data.page)
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
        if group.group_id in pending_role_changes:
            del pending_role_changes[group.group_id]

        await callback.answer("❌ Изменения отменены")
        await callback.message.edit_reply_markup(
            reply_markup=group_access_kb(group, page=callback_data.page)
        )


# =========================== SERVICE MESSAGES HANDLERS ===========================


@group_management_router.callback_query(GroupServiceMessagesMenu.filter())
async def handle_service_messages_callback(
    callback: CallbackQuery,
    callback_data: GroupServiceMessagesMenu,
    stp_repo: MainRequestsRepo,
):
    """Handle service messages settings."""
    user_id = callback.from_user.id
    group_id = callback_data.group_id

    if not await check_user_admin_status(user_id, group_id, callback.bot):
        await callback.answer("❌ У тебя нет прав администратора в этой группе")
        return

    group = await stp_repo.group.get_group(group_id)
    if not group:
        await callback.answer("❌ Группа не найдена в базе данных")
        return

    if group.group_id not in pending_service_messages_changes:
        pending_service_messages_changes[group.group_id] = (
            getattr(group, "service_messages", []) or []
        ).copy()

    current_pending = pending_service_messages_changes[group.group_id]
    category = callback_data.category

    if category in current_pending:
        pending_service_messages_changes[group.group_id] = [
            c for c in current_pending if c != category
        ]
        action = "убрана из удаляемых"
    else:
        pending_service_messages_changes[group.group_id] = current_pending + [category]
        action = "добавлена к удаляемым"

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

    await callback.message.edit_reply_markup(
        reply_markup=group_service_messages_kb(
            group, pending_service_messages_changes[group.group_id], callback_data.page
        )
    )


@group_management_router.callback_query(GroupServiceMessagesApplyMenu.filter())
async def handle_service_messages_apply_callback(
    callback: CallbackQuery,
    callback_data: GroupServiceMessagesApplyMenu,
    stp_repo: MainRequestsRepo,
):
    """Handle service messages apply/cancel."""
    user_id = callback.from_user.id
    group_id = callback_data.group_id

    if not await check_user_admin_status(user_id, group_id, callback.bot):
        await callback.answer("❌ У тебя нет прав администратора в этой группе")
        return

    group = await stp_repo.group.get_group(group_id)
    if not group:
        await callback.answer("❌ Группа не найдена в базе данных")
        return

    if callback_data.action == "apply":
        if group.group_id in pending_service_messages_changes:
            new_categories = pending_service_messages_changes[group.group_id]

            updated_group = await stp_repo.group.update_group(
                group_id=group.group_id, service_messages=new_categories
            )

            if updated_group:
                await callback.answer("✅ Настройки сервисных сообщений применены!")
                del pending_service_messages_changes[group.group_id]

                await callback.message.edit_reply_markup(
                    reply_markup=group_service_messages_kb(
                        updated_group, page=callback_data.page
                    )
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
        if group.group_id in pending_service_messages_changes:
            del pending_service_messages_changes[group.group_id]

        await callback.answer("❌ Изменения отменены")
        await callback.message.edit_reply_markup(
            reply_markup=group_service_messages_kb(group, page=callback_data.page)
        )


# =========================== MEMBERS MANAGEMENT HANDLERS ===========================


@group_management_router.callback_query(GroupMembersMenu.filter())
async def handle_members_pagination(
    callback: CallbackQuery,
    callback_data: GroupMembersMenu,
    stp_repo: MainRequestsRepo,
):
    """Handle members list pagination."""
    user_id = callback.from_user.id
    group_id = callback_data.group_id

    if not await check_user_admin_status(user_id, group_id, callback.bot):
        await callback.answer("❌ У тебя нет прав администратора в этой группе")
        return

    group = await stp_repo.group.get_group(group_id)
    if not group:
        await callback.answer("❌ Группа не найдена в базе данных")
        return

    group_members = await stp_repo.group_member.get_group_members(group.group_id)

    employees = []
    non_employee_users = []

    for group_member in group_members:
        employee = await stp_repo.employee.get_user(user_id=group_member.member_id)
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
            list_page=callback_data.list_page,
        ),
    )

    await callback.answer()


@group_management_router.callback_query(GroupMemberDetailMenu.filter())
async def handle_member_detail(
    callback: CallbackQuery,
    callback_data: GroupMemberDetailMenu,
    stp_repo: MainRequestsRepo,
):
    """Handle member detail view."""
    user_id = callback.from_user.id
    group_id = callback_data.group_id

    if not await check_user_admin_status(user_id, group_id, callback.bot):
        await callback.answer("❌ У тебя нет прав администратора в этой группе")
        return

    group = await stp_repo.group.get_group(group_id)
    if not group:
        await callback.answer("❌ Группа не найдена в базе данных")
        return

    member_name = ""
    member_info = ""

    if callback_data.member_type == "employee":
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
            list_page=callback_data.list_page,
        ),
    )

    await callback.answer()


@group_management_router.callback_query(GroupMemberActionMenu.filter())
async def handle_member_action(
    callback: CallbackQuery,
    callback_data: GroupMemberActionMenu,
    stp_repo: MainRequestsRepo,
):
    """Handle member actions (ban)."""
    user_id = callback.from_user.id
    group_id = callback_data.group_id

    if not await check_user_admin_status(user_id, group_id, callback.bot):
        await callback.answer("❌ У тебя нет прав администратора в этой группе")
        return

    group = await stp_repo.group.get_group(group_id)
    if not group:
        await callback.answer("❌ Группа не найдена в базе данных")
        return

    if callback_data.action == "ban":
        try:
            await callback.bot.ban_chat_member(
                chat_id=group.group_id, user_id=callback_data.member_id
            )

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

            # Return to members list with updated data
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
                    list_page=callback_data.list_page,
                ),
            )

        except Exception as e:
            await callback.answer("❌ Ошибка при бане участника")
            logger.error(f"Failed to ban user {callback_data.member_id}: {e}")

    await callback.answer()

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infrastructure.database.models import Employee
from infrastructure.database.models.STP.group import Group
from tgbot.keyboards.user.main import MainMenu
from tgbot.misc.dicts import roles


class GroupsMenu(CallbackData, prefix="groups"):
    menu: str


class GroupManagementMenu(CallbackData, prefix="group_mgmt"):
    action: str
    group_id: int = 0
    page: int = 1


class GroupSettingsMenu(CallbackData, prefix="group_settings"):
    group_id: int
    menu: str
    page: int = 1


class GroupAccessMenu(CallbackData, prefix="group_access"):
    group_id: int
    role_id: int
    page: int = 1


class GroupAccessApplyMenu(CallbackData, prefix="group_access_apply"):
    group_id: int
    action: str
    page: int = 1


class GroupMembersMenu(CallbackData, prefix="group_members"):
    group_id: int
    page: int = 1
    list_page: int = 1


class GroupMemberDetailMenu(CallbackData, prefix="group_member_detail"):
    group_id: int
    member_id: int
    member_type: str
    page: int = 1
    list_page: int = 1


class GroupMemberActionMenu(CallbackData, prefix="group_member_action"):
    group_id: int
    member_id: int
    action: str
    member_type: str
    page: int = 1
    list_page: int = 1


class GroupServiceMessagesMenu(CallbackData, prefix="group_service_msg"):
    group_id: int
    category: str
    page: int = 1


class GroupServiceMessagesApplyMenu(CallbackData, prefix="group_service_msg_apply"):
    group_id: int
    action: str
    page: int = 1


class GroupRemoveBotMenu(CallbackData, prefix="group_remove_bot"):
    group_id: int
    action: str
    page: int = 1


def groups_kb(group_link: str) -> InlineKeyboardMarkup:
    """Main groups menu keyboard."""
    buttons = [
        [
            InlineKeyboardButton(
                text="📋 Список",
                callback_data=GroupsMenu(menu="management").pack(),
            ),
            InlineKeyboardButton(
                text="💡 Команды",
                callback_data=GroupsMenu(menu="cmds").pack(),
            ),
        ],
        [
            InlineKeyboardButton(text="👋 Пригласить бота", url=group_link),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def group_remove_bot_confirmation_kb(
    group_id: int, page: int = 1
) -> InlineKeyboardMarkup:
    """Confirmation keyboard for removing bot from group."""
    buttons = [
        [
            InlineKeyboardButton(
                text="🤔 Да, удалить",
                callback_data=GroupRemoveBotMenu(
                    group_id=group_id, action="remove", page=page
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=GroupSettingsMenu(
                    group_id=group_id, menu="back", page=page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def group_management_kb(
    groups: list, current_page: int = 1, page_size: int = 8, admin_status: dict = None
) -> InlineKeyboardMarkup:
    """Groups selection keyboard for management."""
    buttons = []

    total_groups = len(groups)
    total_pages = max(1, (total_groups + page_size - 1) // page_size)
    start_index = (current_page - 1) * page_size
    end_index = min(start_index + page_size, total_groups)

    page_groups = groups[start_index:end_index]

    for i in range(0, len(page_groups), 2):
        row = []

        group_id, group_name = page_groups[i]
        display_name = group_name[:30] + "..." if len(group_name) > 30 else group_name
        is_admin = admin_status.get(group_id, False) if admin_status else False
        emoji = "🛡️" if is_admin else "👤"
        row.append(
            InlineKeyboardButton(
                text=f"{emoji} {display_name}",
                callback_data=GroupManagementMenu(
                    action="select_group", group_id=group_id, page=current_page
                ).pack(),
            )
        )

        if i + 1 < len(page_groups):
            group_id, group_name = page_groups[i + 1]
            display_name = (
                group_name[:30] + "..." if len(group_name) > 30 else group_name
            )
            is_admin = admin_status.get(group_id, False) if admin_status else False
            emoji = "🛡️" if is_admin else "👤"
            row.append(
                InlineKeyboardButton(
                    text=f"{emoji} {display_name}",
                    callback_data=GroupManagementMenu(
                        action="select_group", group_id=group_id, page=current_page
                    ).pack(),
                )
            )

        buttons.append(row)

    if total_pages > 1:
        pagination_row = []
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="<",
                    callback_data=GroupManagementMenu(
                        action="page", page=current_page - 1
                    ).pack(),
                )
            )

        pagination_row.append(
            InlineKeyboardButton(
                text=f"{current_page}/{total_pages}", callback_data="noop"
            )
        )

        if current_page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(
                    text=">",
                    callback_data=GroupManagementMenu(
                        action="page", page=current_page + 1
                    ).pack(),
                )
            )

        buttons.append(pagination_row)

    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=MainMenu(menu="groups").pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def group_settings_kb(group: Group, page: int = 1) -> InlineKeyboardMarkup:
    """Complete group settings keyboard."""
    buttons = [
        [
            InlineKeyboardButton(
                text="🛡️ Уровень доступа",
                callback_data=GroupSettingsMenu(
                    group_id=group.group_id, menu="access", page=page
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🟢 Приветствие" if group.new_user_notify else "🔴 Приветствие",
                callback_data=GroupSettingsMenu(
                    group_id=group.group_id, menu="new_user_notify", page=page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🟢 Казино" if group.is_casino_allowed else "🔴 Казино",
                callback_data=GroupSettingsMenu(
                    group_id=group.group_id, menu="is_casino_allowed", page=page
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Сервисные сообщения",
                callback_data=GroupSettingsMenu(
                    group_id=group.group_id, menu="service_messages", page=page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="👥 Состав",
                callback_data=GroupSettingsMenu(
                    group_id=group.group_id, menu="members", page=page
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="♻️ Удалить бота",
                callback_data=GroupRemoveBotMenu(
                    group_id=group.group_id, action="confirm", page=page
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=MainMenu(menu="groups").pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def group_access_kb(
    group: Group, pending_roles: list = None, page: int = 1
) -> InlineKeyboardMarkup:
    """Group access control keyboard."""
    if pending_roles is None:
        pending_roles = group.allowed_roles or []

    buttons = [
        [
            InlineKeyboardButton(
                text="🟢 Только сотрудники"
                if group.remove_unemployed
                else "🔴 Только сотрудники",
                callback_data=GroupSettingsMenu(
                    group_id=group.group_id, menu="remove_unemployed"
                ).pack(),
            ),
        ]
    ]

    # Create role buttons in specific order - put Специалист first
    role_buttons = []

    # Order dialogs: Специалист first, then others
    role_order = [1, 2, 3, 4, 5, 6]  # Специалист first, then others

    for role_id in role_order:
        if role_id in roles and role_id not in [0, 10]:  # Skip unauthorized and root
            role_info = roles[role_id]
            is_allowed = role_id in pending_roles
            status = "🟢" if is_allowed else "🔴"
            button_text = f"{status} {role_info['emoji']} {role_info['name']}"

            role_buttons.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=GroupAccessMenu(
                        group_id=group.group_id, role_id=role_id, page=page
                    ).pack(),
                )
            )

    # Arrange buttons in rows of 2
    for i in range(0, len(role_buttons), 2):
        row = role_buttons[i : i + 2]
        buttons.append(row)

    # Check if there are changes to apply
    current_roles = set(group.allowed_roles or [])
    pending_roles_set = set(pending_roles)
    has_changes = current_roles != pending_roles_set

    if has_changes:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✅ Применить",
                    callback_data=GroupAccessApplyMenu(
                        group_id=group.group_id, action="apply", page=page
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=GroupAccessApplyMenu(
                        group_id=group.group_id, action="cancel", page=page
                    ).pack(),
                ),
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=GroupSettingsMenu(
                    group_id=group.group_id, menu="back", page=page
                ).pack(),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def short_name(full_name: str) -> str:
    """Extract short name from full name."""
    clean_name = full_name.split("(")[0].strip()
    parts = clean_name.split()

    if len(parts) >= 2:
        return " ".join(parts[:2])
    return clean_name


def group_members_kb(
    group_id: int,
    employees: list[Employee] = None,
    users: list = None,
    current_page: int = 1,
    list_page: int = 1,
    members_per_page: int = 8,
) -> InlineKeyboardMarkup:
    """Group members management keyboard."""
    buttons = []

    if employees is None:
        employees = []
    if users is None:
        users = []

    all_members = []

    for employee in employees:
        all_members.append(
            {
                "type": "employee",
                "id": employee.user_id,
                "name": short_name(employee.fullname),
                "role": employee.role,
                "data": employee,
            }
        )

    for user in users:
        username = getattr(user, "username", None)
        display_name = f"@{username}" if username else f"user_{user.id}"
        all_members.append(
            {
                "type": "user",
                "id": user.id,
                "name": f"{display_name}",
                "role": None,
                "data": user,
            }
        )

    if not all_members:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="↩️ Назад",
                    callback_data=GroupSettingsMenu(
                        group_id=group_id, menu="back", page=list_page
                    ).pack(),
                )
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    # Implement pagination
    total_members = len(all_members)
    total_pages = max(1, (total_members + members_per_page - 1) // members_per_page)
    start_index = (current_page - 1) * members_per_page
    end_index = min(start_index + members_per_page, total_members)

    page_members = all_members[start_index:end_index]

    # Add member buttons in pairs
    for i in range(0, len(page_members), 2):
        row = []

        member = page_members[i]
        role_emoji = (
            roles.get(member["role"], {}).get("emoji", "👤") if member["role"] else "👤"
        )
        button_text = f"{role_emoji} {member['name']}"

        row.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=GroupMemberDetailMenu(
                    group_id=group_id,
                    member_id=member["id"],
                    member_type=member["type"],
                    page=current_page,
                    list_page=list_page,
                ).pack(),
            )
        )

        if i + 1 < len(page_members):
            member = page_members[i + 1]
            role_emoji = (
                roles.get(member["role"], {}).get("emoji", "👤")
                if member["role"]
                else "👤"
            )
            button_text = f"{role_emoji} {member['name']}"

            row.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=GroupMemberDetailMenu(
                        group_id=group_id,
                        member_id=member["id"],
                        member_type=member["type"],
                        page=current_page,
                        list_page=list_page,
                    ).pack(),
                )
            )

        buttons.append(row)

    # Add pagination controls if needed
    if total_pages > 1:
        pagination_row = []
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="<",
                    callback_data=GroupMembersMenu(
                        group_id=group_id,
                        page=current_page - 1,
                        list_page=list_page,
                    ).pack(),
                )
            )

        pagination_row.append(
            InlineKeyboardButton(
                text=f"{current_page}/{total_pages}", callback_data="noop"
            )
        )

        if current_page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(
                    text=">",
                    callback_data=GroupMembersMenu(
                        group_id=group_id,
                        page=current_page + 1,
                        list_page=list_page,
                    ).pack(),
                )
            )

        buttons.append(pagination_row)

    # Back button
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=GroupSettingsMenu(
                    group_id=group_id, menu="back", page=list_page
                ).pack(),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def group_member_detail_kb(
    group_id: int,
    member_id: int,
    member_type: str,
    member_name: str,
    page: int = 1,
    list_page: int = 1,
) -> InlineKeyboardMarkup:
    """Member detail keyboard."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"🚫 Забанить {member_name}",
                callback_data=GroupMemberActionMenu(
                    group_id=group_id,
                    member_id=member_id,
                    action="ban",
                    member_type=member_type,
                    page=page,
                    list_page=list_page,
                ).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text=f"👢 Исключить {member_name}",
                callback_data=GroupMemberActionMenu(
                    group_id=group_id,
                    member_id=member_id,
                    action="kick",
                    member_type=member_type,
                    page=page,
                    list_page=list_page,
                ).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=GroupMembersMenu(
                    group_id=group_id,
                    page=page,
                    list_page=list_page,
                ).pack(),
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def group_service_messages_kb(
    group: Group, pending_categories: list = None, page: int = 1
) -> InlineKeyboardMarkup:
    """Service messages management keyboard."""
    if pending_categories is None:
        pending_categories = getattr(group, "service_messages", []) or []

    categories = {
        "all": "🗑️ Все",
        "join": "👋 Вход",
        "leave": "👋 Выход",
        "other": "📦 Прочее",
        "photo": "🖼️ Фото",
        "pin": "📌 Закреп",
        "title": "🏷️ Название",
        "videochat": "📹 Видеозвонки",
    }

    buttons = []
    category_buttons = []

    for category, name in categories.items():
        is_enabled = category in pending_categories
        status = "🟢" if is_enabled else "🔴"
        button_text = f"{status} {name}"

        category_buttons.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=GroupServiceMessagesMenu(
                    group_id=group.group_id, category=category, page=page
                ).pack(),
            )
        )

    for i in range(0, len(category_buttons), 2):
        row = category_buttons[i : i + 2]
        buttons.append(row)

    current_categories = set(getattr(group, "service_messages", []) or [])
    pending_categories_set = set(pending_categories)
    has_changes = current_categories != pending_categories_set

    if has_changes:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✅ Применить",
                    callback_data=GroupServiceMessagesApplyMenu(
                        group_id=group.group_id, action="apply", page=page
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=GroupServiceMessagesApplyMenu(
                        group_id=group.group_id, action="cancel", page=page
                    ).pack(),
                ),
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=GroupSettingsMenu(
                    group_id=group.group_id, menu="back", page=page
                ).pack(),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)

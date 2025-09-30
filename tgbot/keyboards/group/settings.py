from aiogram.filters.callback_data import CallbackData
from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup

from infrastructure.database.models import Employee
from infrastructure.database.models.STP.group import Group
from tgbot.misc.dicts import roles


class GroupSettingsMenu(CallbackData, prefix="group"):
    group_id: int
    menu: str


class GroupAccessMenu(CallbackData, prefix="access"):
    group_id: int
    role_id: int


class GroupAccessApplyMenu(CallbackData, prefix="access_apply"):
    group_id: int
    action: str


class GroupMembersMenu(CallbackData, prefix="group_members"):
    group_id: int
    page: int = 1


class GroupMemberDetailMenu(CallbackData, prefix="group_member_detail"):
    group_id: int
    member_id: int
    member_type: str  # "employee" or "user"
    page: int = 1


class GroupMemberActionMenu(CallbackData, prefix="group_member_action"):
    group_id: int
    member_id: int
    action: str  # "ban"
    member_type: str
    page: int = 1


class GroupServiceMessagesMenu(CallbackData, prefix="service_msg"):
    group_id: int
    category: (
        str  # "all", "join", "leave", "other", "photo", "pin", "title", "videochat"
    )


class GroupServiceMessagesApplyMenu(CallbackData, prefix="service_msg_apply"):
    group_id: int
    action: str  # "apply", "cancel"


def group_settings_keyboard(group: Group, group_link: str) -> InlineKeyboardMarkup:
    """Create keyboard for group settings."""
    # Base keyboard structure
    keyboard = [
        [
            InlineKeyboardButton(
                text="🟢 Приветствие" if group.new_user_notify else "🔴 Приветствие",
                callback_data=GroupSettingsMenu(
                    group_id=group.group_id, menu="new_user_notify"
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🟢 Казино" if group.is_casino_allowed else "🔴 Казино",
                callback_data=GroupSettingsMenu(
                    group_id=group.group_id, menu="is_casino_allowed"
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🛡️ Уровень доступа",
                callback_data=GroupSettingsMenu(
                    group_id=group.group_id, menu="access"
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Сервисные сообщения",
                callback_data=GroupSettingsMenu(
                    group_id=group.group_id, menu="service_messages"
                ).pack(),
            ),
            InlineKeyboardButton(
                text="👥 Состав",
                callback_data=GroupSettingsMenu(
                    group_id=group.group_id, menu="members"
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Копировать приглашение",
                copy_text=CopyTextButton(
                    text=group_link,
                ),
            )
        ],
    ]

    # Add members button

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def group_access_keyboard(
    group: Group, pending_roles: list = None
) -> InlineKeyboardMarkup:
    """Create keyboard for group access dialogs settings."""
    if pending_roles is None:
        pending_roles = group.allowed_roles or []

    role_buttons = []

    # Filter out role 0 and create buttons
    for role_id, role_info in roles.items():
        if role_id == 0 or role_id == 10:
            continue

        is_allowed = role_id in pending_roles
        status = "🟢" if is_allowed else "🔴"
        button_text = f"{status} {role_info['emoji']} {role_info['name']}"

        role_buttons.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=GroupAccessMenu(
                    group_id=group.group_id, role_id=role_id
                ).pack(),
            )
        )

    # Arrange buttons in rows of 2
    buttons = []
    for i in range(0, len(role_buttons), 2):
        row = role_buttons[i : i + 2]
        buttons.append(row)

    # Check if there are changes to apply
    current_roles = set(group.allowed_roles or [])
    pending_roles_set = set(pending_roles)
    has_changes = current_roles != pending_roles_set

    if has_changes:
        # Add apply and cancel buttons
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✅ Применить",
                    callback_data=GroupAccessApplyMenu(
                        group_id=group.group_id, action="apply"
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=GroupAccessApplyMenu(
                        group_id=group.group_id, action="cancel"
                    ).pack(),
                ),
            ]
        )

    # Add back button
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=GroupSettingsMenu(
                    group_id=group.group_id, menu="back"
                ).pack(),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def short_name(full_name: str) -> str:
    """Extract short name from full name."""
    # Remove date info in parentheses if present
    clean_name = full_name.split("(")[0].strip()
    parts = clean_name.split()

    if len(parts) >= 2:
        return " ".join(parts[:2])
    return clean_name


def group_members_keyboard(
    group_id: int,
    employees: list[Employee] = None,
    users: list = None,
    current_page: int = 1,
    members_per_page: int = 8,
) -> InlineKeyboardMarkup:
    """
    Keyboard for displaying group members with pagination.
    Shows employees first with role emojis, then non-employees.
    """
    buttons = []

    if employees is None:
        employees = []
    if users is None:
        users = []

    # Combine all members for pagination
    all_members = []

    # Add employees first
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

    # Add non-employees
    for user in users:
        username = getattr(user, "username", None)
        display_name = f"@{username}" if username else f"user_{user.id}"
        all_members.append(
            {
                "type": "user",
                "id": user.id,
                "name": f"{display_name} ({user.id})",
                "role": None,
                "data": user,
            }
        )

    if not all_members:
        # No members, show only navigation buttons
        buttons.append(
            [
                InlineKeyboardButton(
                    text="↩️ Назад",
                    callback_data=GroupSettingsMenu(
                        group_id=group_id, menu="back"
                    ).pack(),
                )
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    # Calculate pagination
    total_members = len(all_members)
    total_pages = (total_members + members_per_page - 1) // members_per_page

    # Calculate range for current page
    start_idx = (current_page - 1) * members_per_page
    end_idx = start_idx + members_per_page
    page_members = all_members[start_idx:end_idx]

    # Create member buttons (2 per row)
    for i in range(0, len(page_members), 2):
        row = []

        # First member in row
        member = page_members[i]
        if member["type"] == "employee":
            role_emoji = roles.get(member["role"], {}).get("emoji", "")
            if role_emoji:
                role_emoji += " "
            button_text = f"{role_emoji}{member['name']}"
        else:
            button_text = member["name"]

        row.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=GroupMemberDetailMenu(
                    group_id=group_id,
                    member_id=member["id"],
                    member_type=member["type"],
                    page=current_page,
                ).pack(),
            )
        )

        # Second member in row (if exists)
        if i + 1 < len(page_members):
            member = page_members[i + 1]
            if member["type"] == "employee":
                role_emoji = roles.get(member["role"], {}).get("emoji", "")
                if role_emoji:
                    role_emoji += " "
                button_text = f"{role_emoji}{member['name']}"
            else:
                button_text = member["name"]

            row.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=GroupMemberDetailMenu(
                        group_id=group_id,
                        member_id=member["id"],
                        member_type=member["type"],
                        page=current_page,
                    ).pack(),
                )
            )

        buttons.append(row)

    # Add pagination (only if more than one page)
    if total_pages > 1:
        pagination_row = []

        # First button (⏪ or empty)
        if current_page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=GroupMembersMenu(group_id=group_id, page=1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Second button (⬅️ or empty)
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=GroupMembersMenu(
                        group_id=group_id, page=current_page - 1
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Page indicator
        pagination_row.append(
            InlineKeyboardButton(
                text=f"{current_page}/{total_pages}",
                callback_data="noop",
            )
        )

        # Fourth button (➡️ or empty)
        if current_page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=GroupMembersMenu(
                        group_id=group_id, page=current_page + 1
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Fifth button (⏭️ or empty)
        if current_page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏭️",
                    callback_data=GroupMembersMenu(
                        group_id=group_id, page=total_pages
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Add navigation buttons
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=GroupSettingsMenu(group_id=group_id, menu="back").pack(),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def group_service_messages_keyboard(
    group: Group, pending_categories: list = None
) -> InlineKeyboardMarkup:
    """Create keyboard for service messages management."""
    if pending_categories is None:
        pending_categories = getattr(group, "service_messages", []) or []

    # Service message categories with descriptions
    categories = {
        "all": {"name": "Все", "emoji": "🗑️", "desc": "Все сервисные сообщения"},
        "join": {"name": "Вход", "emoji": "👋", "desc": "Вход пользователей"},
        "leave": {"name": "Выход", "emoji": "👋", "desc": "Выход пользователей"},
        "other": {"name": "Прочее", "emoji": "📝", "desc": "Бусты, платежи и др."},
        "photo": {"name": "Фото", "emoji": "🖼️", "desc": "Смена фото чата"},
        "pin": {"name": "Закреп", "emoji": "📌", "desc": "Закрепленные сообщения"},
        "title": {"name": "Название", "emoji": "✏️", "desc": "Смена названия"},
        "videochat": {"name": "Видеозвонки", "emoji": "📹", "desc": "Видеозвонки"},
    }

    category_buttons = []

    # Create buttons for each category
    for category_id, category_info in categories.items():
        is_enabled = category_id in pending_categories
        status = "🟢" if is_enabled else "🔴"
        button_text = f"{status} {category_info['emoji']} {category_info['name']}"

        category_buttons.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=GroupServiceMessagesMenu(
                    group_id=group.group_id, category=category_id
                ).pack(),
            )
        )

    # Arrange buttons in rows of 2
    buttons = []
    for i in range(0, len(category_buttons), 2):
        row = category_buttons[i : i + 2]
        buttons.append(row)

    # Check if there are changes to apply
    current_categories = set(getattr(group, "service_messages", []) or [])
    pending_categories_set = set(pending_categories)
    has_changes = current_categories != pending_categories_set

    if has_changes:
        # Add apply and cancel buttons
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✅ Применить",
                    callback_data=GroupServiceMessagesApplyMenu(
                        group_id=group.group_id, action="apply"
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=GroupServiceMessagesApplyMenu(
                        group_id=group.group_id, action="cancel"
                    ).pack(),
                ),
            ]
        )

    # Add back button
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=GroupSettingsMenu(
                    group_id=group.group_id, menu="back"
                ).pack(),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)

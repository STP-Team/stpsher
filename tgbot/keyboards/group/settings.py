from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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


def group_settings_keyboard(group: Group) -> InlineKeyboardMarkup:
    """Create keyboard for group settings."""
    # Base keyboard structure
    keyboard = [
        [
            InlineKeyboardButton(
                text="🟢 Только сотрудники"
                if group.remove_unemployed
                else "🔴 Только сотрудники",
                callback_data=GroupSettingsMenu(
                    group_id=group.group_id, menu="remove_unemployed"
                ).pack(),
            ),
        ],
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
    ]

    if group.remove_unemployed:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🛡️ Уровень доступа",
                    callback_data=GroupSettingsMenu(
                        group_id=group.group_id, menu="access"
                    ).pack(),
                ),
            ]
        )

    # Add members button
    keyboard.append(
        [
            InlineKeyboardButton(
                text="👥 Состав",
                callback_data=GroupSettingsMenu(
                    group_id=group.group_id, menu="members"
                ).pack(),
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def group_access_keyboard(
    group: Group, pending_roles: list = None
) -> InlineKeyboardMarkup:
    """Create keyboard for group access roles settings."""
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

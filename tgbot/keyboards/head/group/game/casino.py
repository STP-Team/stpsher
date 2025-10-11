from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from stp_database import Employee

from tgbot.keyboards.head.group.main import GroupManagementMenu
from tgbot.keyboards.head.group.members import short_name
from tgbot.keyboards.user.main import MainMenu


class HeadCasinoUserToggle(CallbackData, prefix="head_casino_toggle"):
    user_id: int


class HeadCasinoToggleAll(CallbackData, prefix="head_casino_all"):
    action: str  # "enable_all" or "disable_all" or "toggle_all"


def head_casino_management_kb(
    group_members: list[Employee],
) -> InlineKeyboardMarkup:
    """
    Клавиатура управления казино для руководителей
    """
    buttons = []

    # Если есть участники, добавляем кнопку управления всеми
    if group_members:
        # Проверяем, у всех ли разрешено казино
        all_enabled = all(member.is_casino_allowed for member in group_members)
        all_disabled = all(not member.is_casino_allowed for member in group_members)

        if all_enabled:
            toggle_text = "🟠 Запретить всем"
            action = "disable_all"
        elif all_disabled:
            toggle_text = "🟢 Разрешить всем"
            action = "enable_all"
        else:
            toggle_text = "🔄 Переключить статус всех"
            action = "toggle_all"

        buttons.append(
            [
                InlineKeyboardButton(
                    text=toggle_text,
                    callback_data=HeadCasinoToggleAll(action=action).pack(),
                )
            ]
        )

        # Добавляем участников по 2 в ряд
        for i in range(0, len(group_members), 2):
            row = []

            # Первый участник в ряду
            member = group_members[i]
            status_emoji = "🟢" if member.is_casino_allowed else "🔴"
            member_text = f"{status_emoji} {short_name(member.fullname)}"

            row.append(
                InlineKeyboardButton(
                    text=member_text,
                    callback_data=HeadCasinoUserToggle(user_id=member.id).pack(),
                )
            )

            # Второй участник в ряду (если есть)
            if i + 1 < len(group_members):
                member = group_members[i + 1]
                status_emoji = "🟢" if member.is_casino_allowed else "🔴"
                member_text = f"{status_emoji} {short_name(member.fullname)}"

                row.append(
                    InlineKeyboardButton(
                        text=member_text,
                        callback_data=HeadCasinoUserToggle(user_id=member.id).pack(),
                    )
                )

            buttons.append(row)

    # Добавляем кнопки навигации
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=GroupManagementMenu(menu="game").pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)

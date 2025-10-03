from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.head.group.members import (
    HeadMemberDetailMenu,
    HeadMemberStatusChange,
)
from tgbot.keyboards.user.main import MainMenu


def head_member_status_select_kb(
    member_id: int, page: int = 1, current_role: int = None, is_trainee: bool = False
) -> InlineKeyboardMarkup:
    """Клавиатура для выбора статуса участника (Стажер/Дежурный)"""
    buttons = []

    # Кнопка для статуса "Стажер"
    trainee_text = "✅ Стажер" if is_trainee else "Стажер"
    buttons.append(
        [
            InlineKeyboardButton(
                text=trainee_text,
                callback_data=HeadMemberStatusChange(
                    member_id=member_id, status_type="trainee", page=page
                ).pack(),
            )
        ]
    )

    # Кнопка для статуса "Дежурный" (только если роль 1 или 3)
    if current_role in [1, 3]:
        duty_text = "✅ Дежурный" if current_role == 3 else "Дежурный"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=duty_text,
                    callback_data=HeadMemberStatusChange(
                        member_id=member_id, status_type="duty", page=page
                    ).pack(),
                )
            ]
        )

    # Кнопки навигации
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=HeadMemberDetailMenu(
                    member_id=member_id, page=page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)

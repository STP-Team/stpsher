from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.main import MainMenu


class HeadMemberKPIMenu(CallbackData, prefix="head_member_kpi"):
    member_id: int
    action: str  # "main", "calculator", "salary"
    page: int = 1


def head_member_kpi_kb(
    member_id: int, page: int = 1, current_action: str = "main"
) -> InlineKeyboardMarkup:
    """Клавиатура для KPI участника группы"""
    from tgbot.keyboards.head.group.members import HeadMemberDetailMenu

    buttons = []

    # Основные кнопки KPI меню
    if current_action == "main":
        buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        text="🧮 Нормативы",
                        callback_data=HeadMemberKPIMenu(
                            member_id=member_id, action="calculator", page=page
                        ).pack(),
                    ),
                    InlineKeyboardButton(
                        text="💰 Зарплата",
                        callback_data=HeadMemberKPIMenu(
                            member_id=member_id, action="salary", page=page
                        ).pack(),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Обновить",
                        callback_data=HeadMemberKPIMenu(
                            member_id=member_id, action="main", page=page
                        ).pack(),
                    ),
                ],
            ]
        )
    elif current_action in ["calculator", "salary"]:
        other_action = "salary" if current_action == "calculator" else "calculator"
        other_text = "💰 Зарплата" if other_action == "salary" else "🧮 Нормативы"

        buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        text="🌟 Показатели",
                        callback_data=HeadMemberKPIMenu(
                            member_id=member_id, action="main", page=page
                        ).pack(),
                    ),
                    InlineKeyboardButton(
                        text=other_text,
                        callback_data=HeadMemberKPIMenu(
                            member_id=member_id, action=other_action, page=page
                        ).pack(),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Обновить",
                        callback_data=HeadMemberKPIMenu(
                            member_id=member_id, action=current_action, page=page
                        ).pack(),
                    ),
                ],
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

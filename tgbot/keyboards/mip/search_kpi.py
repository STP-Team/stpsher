from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.main import MainMenu


class SearchUserKPIMenu(CallbackData, prefix="search_user_kpi"):
    user_id: int
    action: str  # "main", "calculator", "salary"
    return_to: str = "search"
    head_id: int = 0


class SearchMemberKPIMenu(CallbackData, prefix="search_member_kpi"):
    member_id: int
    head_id: int
    action: str  # "main", "calculator", "salary"
    page: int = 1


def search_user_kpi_kb(
    user_id: int,
    return_to: str = "search",
    head_id: int = 0,
    current_action: str = "main",
    context: str = "mip",
) -> InlineKeyboardMarkup:
    """
    Клавиатура для KPI пользователя из поиска
    """
    from tgbot.keyboards.common.search import SearchUserResult

    buttons = []

    # Основные кнопки KPI меню
    if current_action == "main":
        buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        text="🧮 Нормативы",
                        callback_data=SearchUserKPIMenu(
                            user_id=user_id,
                            action="calculator",
                            return_to=return_to,
                            head_id=head_id,
                        ).pack(),
                    ),
                    InlineKeyboardButton(
                        text="💰 Зарплата",
                        callback_data=SearchUserKPIMenu(
                            user_id=user_id,
                            action="salary",
                            return_to=return_to,
                            head_id=head_id,
                        ).pack(),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Обновить",
                        callback_data=SearchUserKPIMenu(
                            user_id=user_id,
                            action="main",
                            return_to=return_to,
                            head_id=head_id,
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
                        callback_data=SearchUserKPIMenu(
                            user_id=user_id,
                            action="main",
                            return_to=return_to,
                            head_id=head_id,
                        ).pack(),
                    ),
                    InlineKeyboardButton(
                        text=other_text,
                        callback_data=SearchUserKPIMenu(
                            user_id=user_id,
                            action=other_action,
                            return_to=return_to,
                            head_id=head_id,
                        ).pack(),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Обновить",
                        callback_data=SearchUserKPIMenu(
                            user_id=user_id,
                            action=current_action,
                            return_to=return_to,
                            head_id=head_id,
                        ).pack(),
                    ),
                ],
            ]
        )

    # Кнопки навигации
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ К сотруднику",
                callback_data=SearchUserResult(
                    user_id=user_id,
                    return_to=return_to,
                    head_id=head_id,
                    context=context,
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def search_member_kpi_kb(
    member_id: int, head_id: int, page: int = 1, current_action: str = "main"
) -> InlineKeyboardMarkup:
    """
    Клавиатура для KPI участника группы из поиска
    """
    from tgbot.keyboards.mip.search import HeadMemberDetailMenuForSearch

    buttons = []

    # Основные кнопки KPI меню
    if current_action == "main":
        buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        text="🧮 Нормативы",
                        callback_data=SearchMemberKPIMenu(
                            member_id=member_id,
                            head_id=head_id,
                            action="calculator",
                            page=page,
                        ).pack(),
                    ),
                    InlineKeyboardButton(
                        text="💰 Зарплата",
                        callback_data=SearchMemberKPIMenu(
                            member_id=member_id,
                            head_id=head_id,
                            action="salary",
                            page=page,
                        ).pack(),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Обновить",
                        callback_data=SearchMemberKPIMenu(
                            member_id=member_id,
                            head_id=head_id,
                            action="main",
                            page=page,
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
                        callback_data=SearchMemberKPIMenu(
                            member_id=member_id,
                            head_id=head_id,
                            action="main",
                            page=page,
                        ).pack(),
                    ),
                    InlineKeyboardButton(
                        text=other_text,
                        callback_data=SearchMemberKPIMenu(
                            member_id=member_id,
                            head_id=head_id,
                            action=other_action,
                            page=page,
                        ).pack(),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Обновить",
                        callback_data=SearchMemberKPIMenu(
                            member_id=member_id,
                            head_id=head_id,
                            action=current_action,
                            page=page,
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
                callback_data=HeadMemberDetailMenuForSearch(
                    member_id=member_id, head_id=head_id, page=page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)

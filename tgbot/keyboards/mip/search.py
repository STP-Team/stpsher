from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.search.search import SearchUserResult


class EditUserMenu(CallbackData, prefix="edit_user"):
    """Callback data для редактирования пользователя (только для МИП)"""

    user_id: int
    action: str  # "edit_fullname", "edit_role"


class SelectUserRole(CallbackData, prefix="select_role"):
    """Callback data для выбора роли пользователя (только для МИП)"""

    user_id: int
    role: int


class HeadGroupMenu(CallbackData, prefix="head_group"):
    """Callback data для просмотра группы руководителя"""

    head_id: int


def edit_user_back_kb(user_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура возврата при редактировании пользователя

    :param user_id: ID пользователя
    :return: Объект встроенной клавиатуры
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="↩️ К пользователю",
                callback_data=SearchUserResult(user_id=user_id, context="mip").pack(),
            )
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def role_selection_kb(user_id: int, current_role: int) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора роли пользователя (только для МИП)

    :param user_id: ID пользователя
    :param current_role: Текущая роль пользователя
    :return: Объект встроенной клавиатуры
    """
    from tgbot.misc.dicts import roles

    buttons = []

    # Кнопки выбора ролей (кроме текущей)
    for role_id, role_data in roles.items():
        if role_id != current_role and role_id > 0:  # Исключаем роль 0 и текущую
            role_name = role_data["name"]
            emoji = role_data["emoji"]

            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{emoji} {role_name}",
                        callback_data=SelectUserRole(
                            user_id=user_id, role=role_id
                        ).pack(),
                    )
                ]
            )

    # Кнопка назад
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ К пользователю",
                callback_data=SearchUserResult(user_id=user_id, context="mip").pack(),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)

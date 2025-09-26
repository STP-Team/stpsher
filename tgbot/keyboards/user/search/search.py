from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infrastructure.database.models import Employee
from tgbot.keyboards.user.main import MainMenu
from tgbot.keyboards.user.search.main import UserSearchMenu
from tgbot.misc.helpers import get_role


class UserSearchUserResult(CallbackData, prefix="user_search_user"):
    user_id: int
    return_to: str = "search"


def get_gender_emoji(fullname: str) -> str:
    """Определяет пол по имени и возвращает соответствующий эмодзи"""
    if not fullname:
        return ""

    name_parts = fullname.strip().split()
    if len(name_parts) < 2:
        return ""

    # Берем второе слово (имя) и проверяем окончание
    first_name = name_parts[1].lower()

    # Мужские окончания
    male_endings = [
        "ич",
        "ович",
        "евич",
        "ич",
        "ей",
        "ай",
        "ий",
        "он",
        "ан",
        "ен",
        "ин",
        "им",
        "ем",
        "ам",
        "ум",
        "юр",
        "ур",
        "ор",
        "ер",
        "ир",
        "ар",
    ]
    # Женские окончания
    female_endings = [
        "на",
        "ла",
        "ра",
        "са",
        "та",
        "ка",
        "га",
        "ва",
        "да",
        "за",
        "ма",
        "па",
        "ха",
        "ца",
        "ча",
        "ша",
        "ща",
        "ья",
        "ия",
        "ея",
    ]

    # Проверяем окончания
    for ending in male_endings:
        if first_name.endswith(ending):
            return "👨 "

    for ending in female_endings:
        if first_name.endswith(ending):
            return "👩 "

    return ""


def user_search_results_kb(
    users: list[Employee],
    page: int,
    total_pages: int,
    search_type: str,
) -> InlineKeyboardMarkup:
    """
    Клавиатура результатов поиска для обычных пользователей
    """
    from tgbot.keyboards.group.main import short_name

    buttons = []

    # Кнопки пользователей (по два в строке)
    user_buttons = []
    for user in users:
        # Формат: "Подразделение | Короткое имя"
        division = user.division or "—"
        display_name = f"{division} | {short_name(user.fullname)}"
        role_emoji = get_role(user.role)["emoji"]
        user_buttons.append(
            InlineKeyboardButton(
                text=f"{role_emoji}{display_name}",
                callback_data=UserSearchUserResult(
                    user_id=user.user_id or user.id
                ).pack(),
            )
        )

    # Группируем кнопки по две в строке
    for i in range(0, len(user_buttons), 2):
        row = user_buttons[i : i + 2]
        buttons.append(row)

    # Пагинация (только если больше одной страницы)
    if total_pages > 1:
        pagination_row = []

        # Первая кнопка (⏪ или пусто)
        if page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=UserSearchMenu(menu=search_type, page=1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Вторая кнопка (⬅️ или пусто)
        if page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=UserSearchMenu(
                        menu=search_type, page=page - 1
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Центральная кнопка - индикатор страницы
        pagination_row.append(
            InlineKeyboardButton(
                text=f"{page}/{total_pages}",
                callback_data="noop",
            )
        )

        # Четвертая кнопка (➡️ или пусто)
        if page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=UserSearchMenu(
                        menu=search_type, page=page + 1
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Пятая кнопка (⏭️ или пусто)
        if page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏭️",
                    callback_data=UserSearchMenu(
                        menu=search_type, page=total_pages
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Кнопки "Назад" и "Домой"
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="search").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def user_search_back_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой "Назад" для поиска обычных пользователей
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="search").pack()
            )
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def user_user_detail_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура для просмотра пользователя обычными пользователями (без кнопок редактирования)

    :return: Объект встроенной клавиатуры
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="search").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

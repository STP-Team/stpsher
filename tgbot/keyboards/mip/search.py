from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infrastructure.database.models import User
from tgbot.keyboards.user.main import MainMenu


class SearchMenu(CallbackData, prefix="search"):
    menu: str
    page: int = 1


class SearchUserResult(CallbackData, prefix="search_user"):
    user_id: int
    return_to: str = "search"  # Откуда пришли (search, head_group)
    head_id: int = 0  # ID руководителя


class HeadGroupMenu(CallbackData, prefix="head_group"):
    head_id: int
    page: int = 1


class EditUserMenu(CallbackData, prefix="edit_user"):
    user_id: int
    action: str  # "edit_fullname"


def search_main_kb() -> InlineKeyboardMarkup:
    """
    Главная клавиатура поиска сотрудников

    :return: Объект встроенной клавиатуры для поиска
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="👤 Специалисты",
                callback_data=SearchMenu(menu="specialists").pack(),
            ),
            InlineKeyboardButton(
                text="👔 Руководители", callback_data=SearchMenu(menu="heads").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔍 Поиск",
                callback_data=SearchMenu(menu="start_search").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def user_detail_kb(
    user_id: int,
    return_to: str = "search",
    head_id: int = 0,
    can_edit: bool = True,
    is_head: bool = False,
    head_user_id: int = 0,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для детального просмотра пользователя

    :param user_id: ID пользователя
    :param return_to: Откуда пришли (для навигации назад)
    :param head_id: ID руководителя (если пришли из группы)
    :param can_edit: Можно ли редактировать пользователя
    :param is_head: Является ли пользователь руководителем
    :param head_user_id: ID пользователя-руководителя (для просмотра группы)
    :return: Объект встроенной клавиатуры
    """
    buttons = []

    # Кнопка просмотра группы (для руководителей)
    if is_head and head_user_id:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="👥 Показать группу",
                    callback_data=HeadGroupMenu(head_id=head_user_id, page=1).pack(),
                )
            ]
        )

    # Кнопка редактирования (если разрешено)
    if can_edit:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✏️ Изменить ФИО",
                    callback_data=EditUserMenu(
                        user_id=user_id, action="edit_fullname"
                    ).pack(),
                )
            ]
        )

    # Навигация назад
    if return_to == "head_group" and head_id:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="↩️ К группе",
                    callback_data=HeadGroupMenu(head_id=head_id, page=1).pack(),
                )
            ]
        )
    else:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="↩️ Назад",
                    callback_data=MainMenu(menu="search").pack(),
                ),
                InlineKeyboardButton(
                    text="🏠 Домой",
                    callback_data=MainMenu(menu="main").pack(),
                ),
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def head_group_kb(
    users: list[User], head_id: int, page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    """
    Клавиатура группы руководителя (список его сотрудников)

    :param users: Список сотрудников
    :param head_id: Имя руководителя
    :param page: Текущая страница
    :param total_pages: Общее количество страниц
    :return: Объект встроенной клавиатуры
    """
    buttons = []

    # Кнопки сотрудников
    for user in users:
        button_text = f"👤 {user.fullname} | {user.division}"
        callback_data = SearchUserResult(
            user_id=user.user_id, return_to="head_group", head_id=head_id
        ).pack()
        buttons.append(
            [
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=callback_data,
                )
            ]
        )

    # Пагинация (если больше одной страницы)
    if total_pages > 1:
        pagination_row = []

        # ⏪
        if page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=HeadGroupMenu(head_id=head_id, page=1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # ◀️
        if page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="◀️",
                    callback_data=HeadGroupMenu(head_id=head_id, page=page - 1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Номер страницы
        pagination_row.append(
            InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")
        )

        # ▶️
        if page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(
                    text="▶️",
                    callback_data=HeadGroupMenu(head_id=head_id, page=page + 1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # ⏩
        if page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏩",
                    callback_data=HeadGroupMenu(
                        head_id=head_id, page=total_pages
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Навигация
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=MainMenu(menu="search").pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def edit_user_back_kb(user_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура возврата при редактировании пользователя

    :param user_id: ID пользователя
    :return: Объект встроенной клавиатуры
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=SearchUserResult(user_id=user_id).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def search_results_kb(
    users: list[User], page: int = 1, total_pages: int = 1, search_type: str = "all"
) -> InlineKeyboardMarkup:
    """
    Клавиатура с результатами поиска (пагинированная)

    :param users: Список найденных пользователей
    :param page: Текущая страница
    :param total_pages: Общее количество страниц
    :param search_type: Тип поиска (all, specialists, heads)
    :return: Объект встроенной клавиатуры с результатами
    """
    buttons = []

    # Кнопки с результатами поиска
    for user in users:
        if not user.user_id:
            continue

        button_text = f"👤 {user.fullname} | {user.division}"
        callback_data = SearchUserResult(
            user_id=user.user_id, return_to=search_type, head_id=0
        ).pack()
        buttons.append(
            [
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=callback_data,
                )
            ]
        )

    # Пагинация (только если больше одной страницы)
    if total_pages > 1:
        pagination_row = []

        # Кнопка "В начало" (⏪ или пусто)
        if page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=SearchMenu(menu=search_type, page=1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Кнопка "Назад" (◀️ или пусто)
        if page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="◀️",
                    callback_data=SearchMenu(menu=search_type, page=page - 1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Центральная кнопка с номером страницы
        pagination_row.append(
            InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")
        )

        # Кнопка "Вперед" (▶️ или пусто)
        if page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(
                    text="▶️",
                    callback_data=SearchMenu(menu=search_type, page=page + 1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Кнопка "В конец" (⏩ или пусто)
        if page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏩",
                    callback_data=SearchMenu(menu=search_type, page=total_pages).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Кнопки навигации
    navigation_row = [
        InlineKeyboardButton(
            text="🔍 Новый поиск",
            callback_data=SearchMenu(menu="start_search").pack(),
        ),
        InlineKeyboardButton(
            text="↩️ Назад", callback_data=MainMenu(menu="search").pack()
        ),
    ]
    buttons.append(navigation_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def search_back_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура возврата к поиску

    :return: Объект встроенной клавиатуры для возврата
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

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

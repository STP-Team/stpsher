from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infrastructure.database.models import Employee
from tgbot.keyboards.user.main import MainMenu
from tgbot.services.schedule.parsers import CommonUtils


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
    action: str  # "edit_fullname", "edit_role"


class SelectUserRole(CallbackData, prefix="select_role"):
    user_id: int
    role: int  # 1, 2, 3


class ViewUserSchedule(CallbackData, prefix="view_schedule"):
    user_id: int
    return_to: str = "search"  # Откуда пришли (search, head_group)
    head_id: int = 0  # ID руководителя
    month_idx: int = 0  # Индекс месяца для просмотра (0 = текущий)


class MipScheduleNavigation(CallbackData, prefix="mip_sched"):
    """Callback data для навигации по месяцам в расписании пользователя для МИП"""

    action: str  # "prev", "next", "-", "detailed", "compact"
    user_id: int
    month_idx: int  # индекс месяца (1-12)
    return_to: str = "search"  # Откуда пришли (search, head_group)
    head_id: int = 0  # ID руководителя


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
                text="👑 Руководители", callback_data=SearchMenu(menu="heads").pack()
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
    buttons = [
        [
            InlineKeyboardButton(
                text="📅 График",
                callback_data=ViewUserSchedule(
                    user_id=user_id, return_to=return_to, head_id=head_id
                ).pack(),
            )
        ]
    ]

    # Кнопка просмотра группы (для руководителей)
    if is_head and head_user_id:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="❤️ Группа",
                    callback_data=HeadGroupMenu(head_id=head_user_id, page=1).pack(),
                )
            ]
        )

    # Кнопки редактирования (если разрешено)
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
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🛡️ Уровень доступа",
                    callback_data=EditUserMenu(
                        user_id=user_id, action="edit_role"
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
    users: list[Employee], head_id: int, page: int = 1, total_pages: int = 1
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
        gender_emoji = CommonUtils.get_gender_emoji(user.fullname)
        button_text = f"{gender_emoji} {user.fullname} | {user.division}"
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


def short_name(full_name: str) -> str:
    """Extract short name from full name."""
    # Remove date info in parentheses if present
    clean_name = full_name.split("(")[0].strip()
    parts = clean_name.split()

    if len(parts) >= 2:
        return " ".join(parts[:2])
    return clean_name


class HeadGroupMembersMenuForSearch(CallbackData, prefix="head_group_members_search"):
    head_id: int
    page: int = 1


class HeadMemberDetailMenuForSearch(CallbackData, prefix="head_member_detail_search"):
    member_id: int
    head_id: int
    page: int = 1


def head_group_members_kb_for_search(
    members,
    current_page: int = 1,
    members_per_page: int = 8,
    head_id: int = 0,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для отображения участников группы с пагинацией для поиска MIP.
    Отображает 2 участника в ряд, по умолчанию 8 участников на страницу (4 ряда).
    """
    buttons = []

    if not members:
        # Если нет участников, показываем только кнопки навигации
        buttons.append(
            [
                InlineKeyboardButton(
                    text="↩️ Назад",
                    callback_data=MainMenu(menu="search").pack(),
                ),
                InlineKeyboardButton(
                    text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
                ),
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    # Рассчитываем пагинацию
    total_members = len(members)
    total_pages = (total_members + members_per_page - 1) // members_per_page

    # Рассчитываем диапазон участников для текущей страницы
    start_idx = (current_page - 1) * members_per_page
    end_idx = start_idx + members_per_page
    page_members = members[start_idx:end_idx]

    # Создаем кнопки для участников (2 в ряд)
    for i in range(0, len(page_members), 2):
        row = []

        # Первый участник в ряду
        member = page_members[i]
        member_short_name = short_name(member.fullname)

        # Добавляем эмодзи для неавторизованных пользователей
        status_emoji = "🔒 " if not member.user_id else ""
        role_emoji = {3: "👮 ", 10: "🔨 "}.get(member.role, "")
        button_text = f"{status_emoji}{role_emoji}{member_short_name}"

        row.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=HeadMemberDetailMenuForSearch(
                    member_id=member.id, head_id=head_id, page=current_page
                ).pack(),
            )
        )

        # Второй участник в ряду (если есть)
        if i + 1 < len(page_members):
            member = page_members[i + 1]
            member_short_name = short_name(member.fullname)
            status_emoji = "🔒 " if not member.user_id else ""
            role_emoji = {3: "👮 ", 10: "🔨 "}.get(member.role, "")
            button_text = f"{status_emoji}{role_emoji}{member_short_name}"

            row.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=HeadMemberDetailMenuForSearch(
                        member_id=member.id, head_id=head_id, page=current_page
                    ).pack(),
                )
            )

        buttons.append(row)

    # Добавляем пагинацию (только если больше одной страницы)
    if total_pages > 1:
        pagination_row = []

        # Клавиатура пагинации: [⏪] [⬅️] [страница] [➡️] [⏭️]

        # Первая кнопка (⏪ или пусто)
        if current_page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=HeadGroupMembersMenuForSearch(
                        head_id=head_id, page=1
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Вторая кнопка (⬅️ или пусто)
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=HeadGroupMembersMenuForSearch(
                        head_id=head_id, page=current_page - 1
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Центральная кнопка - Индикатор страницы (всегда видна)
        pagination_row.append(
            InlineKeyboardButton(
                text=f"{current_page}/{total_pages}",
                callback_data="noop",
            )
        )

        # Четвертая кнопка (➡️ или пусто)
        if current_page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=HeadGroupMembersMenuForSearch(
                        head_id=head_id, page=current_page + 1
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Пятая кнопка (⏭️ или пусто)
        if current_page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏭️",
                    callback_data=HeadGroupMembersMenuForSearch(
                        head_id=head_id, page=total_pages
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Добавляем кнопки навигации
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


def head_member_detail_kb_for_search(
    member_id: int, head_id: int, page: int = 1, member_role: int = None
) -> InlineKeyboardMarkup:
    """
    Клавиатура для детального просмотра участника группы из поиска
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="📅 График",
                callback_data=HeadMemberActionMenuForSearch(
                    member_id=member_id, head_id=head_id, action="schedule", page=page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🌟 Показатели",
                callback_data=HeadMemberActionMenuForSearch(
                    member_id=member_id, head_id=head_id, action="kpi", page=page
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🏮 Игровой профиль",
                callback_data=HeadMemberActionMenuForSearch(
                    member_id=member_id,
                    head_id=head_id,
                    action="game_profile",
                    page=page,
                ).pack(),
            ),
        ],
    ]

    # Добавляем кнопку смены роли только для специалистов (роль 1) и дежурных (роль 3)
    if member_role in [1, 3]:
        role_button_text = (
            "👮 Сделать дежурным" if member_role == 1 else "👤 Сделать спецом"
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text=role_button_text,
                    callback_data=HeadMemberRoleChangeForSearch(
                        member_id=member_id, head_id=head_id, page=page
                    ).pack(),
                ),
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=HeadGroupMembersMenuForSearch(
                    head_id=head_id, page=page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


class HeadMemberActionMenuForSearch(CallbackData, prefix="head_member_action_search"):
    member_id: int
    head_id: int
    action: str  # "schedule", "kpi", or "game_profile"
    page: int = 1


class HeadMemberRoleChangeForSearch(CallbackData, prefix="head_member_role_search"):
    member_id: int
    head_id: int
    page: int = 1


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
    users: list[Employee], page: int = 1, total_pages: int = 1, search_type: str = "all"
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

        gender_emoji = CommonUtils.get_gender_emoji(user.fullname)
        button_text = f"{gender_emoji} {user.fullname} | {user.division}"
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


def schedule_back_to_user_kb(
    user_id: int, return_to: str = "search", head_id: int = 0
) -> InlineKeyboardMarkup:
    """
    Клавиатура для возврата к деталям пользователя из расписания

    :param user_id: ID пользователя
    :param return_to: Откуда пришли (search, head_group)
    :param head_id: ID руководителя (если пришли из группы)
    :return: Объект встроенной клавиатуры
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="↩️ К сотруднику",
                callback_data=SearchUserResult(
                    user_id=user_id, return_to=return_to, head_id=head_id
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Список месяцев на русском языке
MONTHS_RU = [
    "январь",
    "февраль",
    "март",
    "апрель",
    "май",
    "июнь",
    "июль",
    "август",
    "сентябрь",
    "октябрь",
    "ноябрь",
    "декабрь",
]

# Эмодзи для месяцев
MONTH_EMOJIS = {
    1: "❄️",
    2: "💙",
    3: "🌸",
    4: "🌷",
    5: "🌻",
    6: "☀️",
    7: "🏖️",
    8: "🌾",
    9: "🍂",
    10: "🎃",
    11: "🍁",
    12: "🎄",
}


def get_month_name_by_index(month_idx: int) -> str:
    """Получает название месяца по индексу (1-12)"""
    if 1 <= month_idx <= 12:
        return MONTHS_RU[month_idx - 1]
    return "январь"


def get_month_index_by_name(month_name: str) -> int:
    """Получает индекс месяца по названию"""
    try:
        return MONTHS_RU.index(month_name.lower()) + 1
    except (ValueError, AttributeError):
        return 1


def user_schedule_with_month_kb(
    user_id: int,
    current_month: str,
    return_to: str = "search",
    head_id: int = 0,
    is_detailed: bool = False,
) -> InlineKeyboardMarkup:
    """
    Клавиатура расписания пользователя с навигацией по месяцам

    :param user_id: ID пользователя
    :param current_month: Текущий выбранный месяц (название)
    :param return_to: Откуда пришли (search, head_group)
    :param head_id: ID руководителя (если пришли из группы)
    :param is_detailed: Текущий режим отображения (True - детальный, False - компактный)
    :return: Объект встроенной клавиатуры
    """
    current_month_idx = get_month_index_by_name(current_month)

    # Получаем предыдущий и следующий месяцы
    prev_month_idx = current_month_idx - 1 if current_month_idx > 1 else 12
    next_month_idx = current_month_idx + 1 if current_month_idx < 12 else 1

    # Эмодзи для текущего месяца
    month_emoji = MONTH_EMOJIS.get(current_month_idx, "📅")

    # Создаем ряд навигации по месяцам
    nav_row = [
        InlineKeyboardButton(
            text="◀️",
            callback_data=MipScheduleNavigation(
                action="prev",
                user_id=user_id,
                month_idx=prev_month_idx,
                return_to=return_to,
                head_id=head_id,
            ).pack(),
        ),
        InlineKeyboardButton(
            text=f"{month_emoji} {current_month.capitalize()}",
            callback_data=MipScheduleNavigation(
                action="-",
                user_id=user_id,
                month_idx=current_month_idx,
                return_to=return_to,
                head_id=head_id,
            ).pack(),
        ),
        InlineKeyboardButton(
            text="▶️",
            callback_data=MipScheduleNavigation(
                action="next",
                user_id=user_id,
                month_idx=next_month_idx,
                return_to=return_to,
                head_id=head_id,
            ).pack(),
        ),
    ]

    # Определяем текст и действие для кнопки переключения режима
    if is_detailed:
        toggle_text = "📋 Кратко"
        toggle_action = "compact"
    else:
        toggle_text = "📋 Подробнее"
        toggle_action = "detailed"

    buttons = [
        nav_row,  # Ряд навигации по месяцам
        [
            InlineKeyboardButton(
                text=toggle_text,
                callback_data=MipScheduleNavigation(
                    action=toggle_action,
                    user_id=user_id,
                    month_idx=current_month_idx,
                    return_to=return_to,
                    head_id=head_id,
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ К сотруднику",
                callback_data=SearchUserResult(
                    user_id=user_id, return_to=return_to, head_id=head_id
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def role_selection_kb(user_id: int, current_role: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора роли пользователя

    :param user_id: ID пользователя
    :param current_role: Текущая роль пользователя (чтобы скрыть кнопку)
    :return: Объект встроенной клавиатуры для выбора роли
    """
    # Все возможные роли в нужном порядке
    role_buttons = []

    # Специалист (1)
    if current_role != 1:
        role_buttons.append(
            InlineKeyboardButton(
                text="👤 Специалист",
                callback_data=SelectUserRole(user_id=user_id, role=1).pack(),
            )
        )

    # Дежурный (3)
    if current_role != 3:
        role_buttons.append(
            InlineKeyboardButton(
                text="🚨 Дежурный",
                callback_data=SelectUserRole(user_id=user_id, role=3).pack(),
            )
        )

    # Руководитель (2)
    if current_role != 2:
        role_buttons.append(
            InlineKeyboardButton(
                text="👑 Руководитель",
                callback_data=SelectUserRole(user_id=user_id, role=2).pack(),
            )
        )

    # Создаем строки по 2 кнопки
    buttons = []
    for i in range(0, len(role_buttons), 2):
        row = role_buttons[i : i + 2]
        buttons.append(row)

    # Добавляем кнопки навигации
    buttons.append(
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
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infrastructure.database.models import Employee
from tgbot.keyboards.user.main import MainMenu


class SearchUserResult(CallbackData, prefix="search_user"):
    user_id: int
    return_to: str = "search"  # Откуда пришли (search, head_search, etc.)
    head_id: int = 0  # ID руководителя
    context: str = "mip"  # Контекст использования (mip, head)


class ViewUserSchedule(CallbackData, prefix="view_schedule"):
    user_id: int
    return_to: str = "search"  # Откуда пришли
    head_id: int = 0  # ID руководителя
    month_idx: int = 0  # Индекс месяца для просмотра (0 = текущий)
    context: str = "mip"  # Контекст использования (mip, head)


class ViewUserKPI(CallbackData, prefix="view_kpi"):
    user_id: int
    return_to: str = "search"  # Откуда пришли
    head_id: int = 0  # ID руководителя
    context: str = "mip"  # Контекст использования (mip, head)


class HeadUserStatusSelect(CallbackData, prefix="head_user_status_select"):
    user_id: int
    return_to: str = "search"
    head_id: int = 0
    context: str = "head"


class HeadUserStatusChange(CallbackData, prefix="head_user_status_change"):
    user_id: int
    status_type: str  # "trainee" or "duty"
    return_to: str = "search"
    head_id: int = 0
    context: str = "head"


class ScheduleNavigation(CallbackData, prefix="sched_nav"):
    """Callback data для навигации по месяцам в расписании пользователя"""

    action: str  # "prev", "next", "-", "detailed", "compact"
    user_id: int
    month_idx: int  # индекс месяца (1-12)
    return_to: str = "search"  # Откуда пришли
    head_id: int = 0  # ID руководителя
    context: str = "mip"  # Контекст использования (mip, head)


def search_results_kb(
    users: list[Employee],
    page: int,
    total_pages: int,
    search_type: str,
    context: str = "mip",
    back_callback: str = "search",
) -> InlineKeyboardMarkup:
    """
    Клавиатура результатов поиска пользователей

    :param users: Список найденных пользователей
    :param page: Текущая страница
    :param total_pages: Общее количество страниц
    :param search_type: Тип поиска
    :param context: Контекст использования (mip, head)
    :param back_callback: Callback для кнопки "Назад"
    :return: Объект встроенной клавиатуры
    """
    buttons = []

    # Кнопки пользователей
    for user in users:
        status_emoji = ""
        if not user.user_id:
            status_emoji = "🔒 "
        elif user.role == 3:
            status_emoji = "👮 "
        elif user.role == 4:
            status_emoji = "🔨 "

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{status_emoji}{user.fullname}",
                    callback_data=SearchUserResult(
                        user_id=user.user_id or user.id, context=context
                    ).pack(),
                )
            ]
        )

    # Навигация по страницам
    nav_buttons = []
    if page > 1:
        from tgbot.keyboards.mip.search import SearchMenu

        nav_buttons.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=SearchMenu(menu=search_type, page=page - 1).pack(),
            )
        )

    if page < total_pages:
        from tgbot.keyboards.mip.search import SearchMenu

        nav_buttons.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=SearchMenu(menu=search_type, page=page + 1).pack(),
            )
        )

    if nav_buttons:
        buttons.append(nav_buttons)

    # Кнопка "Назад"
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu=back_callback).pack()
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def user_detail_kb(
    user_id: int,
    return_to: str = "search",
    head_id: int = 0,
    context: str = "mip",
    show_edit_buttons: bool = True,
    is_head: bool = False,
    head_user_id: int = 0,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для детального просмотра пользователя

    :param user_id: ID пользователя
    :param return_to: Куда возвращаться
    :param head_id: ID руководителя (если применимо)
    :param context: Контекст использования (mip, head)
    :param show_edit_buttons: Показывать ли кнопки редактирования
    :param is_head: Является ли пользователь руководителем
    :param head_user_id: ID пользователя-руководителя
    :return: Объект встроенной клавиатуры
    """
    buttons = []

    # Основные кнопки (расписание и KPI) - показываем всегда
    action_buttons = [
        InlineKeyboardButton(
            text="📅 Расписание",
            callback_data=ViewUserSchedule(
                user_id=user_id, return_to=return_to, head_id=head_id, context=context
            ).pack(),
        ),
        InlineKeyboardButton(
            text="🌟 KPI",
            callback_data=ViewUserKPI(
                user_id=user_id, return_to=return_to, head_id=head_id, context=context
            ).pack(),
        ),
    ]
    buttons.append(action_buttons)

    # Кнопки редактирования - только для MIP контекста
    if show_edit_buttons and context == "mip":
        from tgbot.keyboards.mip.search import EditUserMenu

        edit_buttons = [
            InlineKeyboardButton(
                text="✏️ ФИО",
                callback_data=EditUserMenu(
                    user_id=user_id, action="edit_fullname"
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🛡️ Роль",
                callback_data=EditUserMenu(user_id=user_id, action="edit_role").pack(),
            ),
        ]
        buttons.append(edit_buttons)
    elif show_edit_buttons and context == "head":
        edit_buttons = [
            InlineKeyboardButton(
                text="⚙️ Изменить статус",
                callback_data=HeadUserStatusSelect(
                    user_id=user_id,
                    return_to=return_to,
                    head_id=head_id,
                    context=context,
                ).pack(),
            )
        ]
        buttons.append(edit_buttons)

    # Кнопка группы для руководителей
    if is_head:
        from tgbot.keyboards.mip.search import HeadGroupMenu

        buttons.append(
            [
                InlineKeyboardButton(
                    text="👥 Группа",
                    callback_data=HeadGroupMenu(head_id=head_user_id).pack(),
                )
            ]
        )

    # Кнопка назад
    if return_to == "search":
        back_callback = "search" if context == "mip" else "main"
    else:
        back_callback = return_to

    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu=back_callback).pack()
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def search_back_kb(context: str = "mip") -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой "Назад" для поиска

    :param context: Контекст использования (mip, head)
    :return: Объект встроенной клавиатуры
    """
    back_callback = "search" if context == "mip" else "main"

    buttons = [
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu=back_callback).pack()
            )
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def head_user_status_select_kb(
    user_id: int,
    return_to: str = "search",
    head_id: int = 0,
    context: str = "head",
    current_role: int = None,
    is_trainee: bool = False,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора статуса пользователя (Стажер/Дежурный) для руководителей
    """
    buttons = []

    # Кнопка для статуса "Стажер"
    trainee_text = "✅ Стажер" if is_trainee else "Стажер"
    buttons.append(
        [
            InlineKeyboardButton(
                text=trainee_text,
                callback_data=HeadUserStatusChange(
                    user_id=user_id,
                    status_type="trainee",
                    return_to=return_to,
                    head_id=head_id,
                    context=context,
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
                    callback_data=HeadUserStatusChange(
                        user_id=user_id,
                        status_type="duty",
                        return_to=return_to,
                        head_id=head_id,
                        context=context,
                    ).pack(),
                )
            ]
        )

    # Кнопки навигации
    buttons.append(
        [
            InlineKeyboardButton(
                text="↙️ Назад",
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


def user_schedule_with_month_kb(
    user_id: int,
    current_month: str,
    return_to: str = "search",
    head_id: int = 0,
    is_detailed: bool = False,
    context: str = "mip",
) -> InlineKeyboardMarkup:
    """
    Клавиатура для просмотра расписания пользователя с навигацией по месяцам

    :param user_id: ID пользователя
    :param current_month: Текущий месяц
    :param return_to: Куда возвращаться
    :param head_id: ID руководителя
    :param is_detailed: Детальный ли вид
    :param context: Контекст использования (mip, head)
    :return: Объект встроенной клавиатуры
    """

    # Получаем индекс текущего месяца
    month_names = [
        "Январь",
        "Февраль",
        "Март",
        "Апрель",
        "Май",
        "Июнь",
        "Июль",
        "Август",
        "Сентябрь",
        "Октябрь",
        "Ноябрь",
        "Декабрь",
    ]

    try:
        current_month_idx = month_names.index(current_month) + 1
    except ValueError:
        current_month_idx = 1

    buttons = []

    # Навигация по месяцам
    nav_buttons = []
    prev_month_idx = current_month_idx - 1 if current_month_idx > 1 else 12
    next_month_idx = current_month_idx + 1 if current_month_idx < 12 else 1

    nav_buttons.append(
        InlineKeyboardButton(
            text="◀️",
            callback_data=ScheduleNavigation(
                action="prev",
                user_id=user_id,
                month_idx=prev_month_idx,
                return_to=return_to,
                head_id=head_id,
                context=context,
            ).pack(),
        )
    )

    nav_buttons.append(
        InlineKeyboardButton(
            text=current_month,
            callback_data=ScheduleNavigation(
                action="-",
                user_id=user_id,
                month_idx=current_month_idx,
                return_to=return_to,
                head_id=head_id,
                context=context,
            ).pack(),
        )
    )

    nav_buttons.append(
        InlineKeyboardButton(
            text="▶️",
            callback_data=ScheduleNavigation(
                action="next",
                user_id=user_id,
                month_idx=next_month_idx,
                return_to=return_to,
                head_id=head_id,
                context=context,
            ).pack(),
        )
    )

    buttons.append(nav_buttons)

    # Переключение детального/компактного вида
    detail_action = "compact" if is_detailed else "detailed"
    detail_text = "📋 Компактно" if is_detailed else "📄 Подробно"

    buttons.append(
        [
            InlineKeyboardButton(
                text=detail_text,
                callback_data=ScheduleNavigation(
                    action=detail_action,
                    user_id=user_id,
                    month_idx=current_month_idx,
                    return_to=return_to,
                    head_id=head_id,
                    context=context,
                ).pack(),
            )
        ]
    )

    # Кнопка назад
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ К информации",
                callback_data=SearchUserResult(
                    user_id=user_id,
                    return_to=return_to,
                    head_id=head_id,
                    context=context,
                ).pack(),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)

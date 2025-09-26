from typing import List

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infrastructure.database.models import Employee
from tgbot.keyboards.user.main import MainMenu
from tgbot.keyboards.user.schedule.main import MONTH_EMOJIS
from tgbot.misc.helpers import get_role


class SearchFilterToggleMenu(CallbackData, prefix="sf_toggle"):
    menu: str  # "specialists" или "heads"
    filter_name: str  # "НЦК", "НТП1" или "НТП2"
    page: int = 1
    current_filters: str = "НЦК,НТП1,НТП2"  # текущие активные фильтры


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


class HeadUserCasinoToggle(CallbackData, prefix="head_user_casino"):
    user_id: int
    return_to: str = "search"
    head_id: int = 0
    context: str = "head"


class ViewUserKPICalculator(CallbackData, prefix="view_kpi_calc"):
    user_id: int
    return_to: str = "search"
    head_id: int = 0
    context: str = "mip"


class ViewUserKPISalary(CallbackData, prefix="view_kpi_salary"):
    user_id: int
    return_to: str = "search"
    head_id: int = 0
    context: str = "mip"


class SearchHeadGroupMembers(CallbackData, prefix="search_head_group"):
    head_id: int
    page: int = 1
    context: str = "mip"


class SearchHeadGroupMemberDetail(CallbackData, prefix="search_head_member"):
    head_id: int
    member_id: int
    page: int = 1
    context: str = "mip"


class ScheduleNavigation(CallbackData, prefix="sched_nav"):
    """Callback data для навигации по месяцам в расписании пользователя"""

    action: str  # "prev", "next", "-", "detailed", "compact"
    user_id: int
    month_idx: int  # индекс месяца (1-12)
    return_to: str = "search"  # Откуда пришли
    head_id: int = 0  # ID руководителя
    context: str = "mip"  # Контекст использования (mip, head)


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

    # Если не удалось определить, возвращаем пустую строку
    return ""


def parse_filters(filters_str: str) -> set[str]:
    """
    Парсит фильтры
    :param filters_str: Список фильтров
    :return:
    """
    if not filters_str:
        return {"НЦК", "НТП1", "НТП2"}
    return set(
        filter_name.strip()
        for filter_name in filters_str.split(",")
        if filter_name.strip()
    )


def filters_to_string(filters_set: set[str]) -> str:
    """
    Конвертирует список фильтров в строку, разделенную запятыми
    :param filters_set: Сет фильтров
    :return:
    """
    return ",".join(sorted(filters_set))


def toggle_filter(current_filters: str, filter_to_toggle: str) -> str:
    """
    Включает или выключает фильтры и возвращает новый список фильтров
    :param current_filters: Текущие активные фильтры
    :param filter_to_toggle: Изменяемые фильтры
    :return:
    """
    filters_set = parse_filters(current_filters)

    if filter_to_toggle in filters_set:
        filters_set.discard(filter_to_toggle)
    else:
        filters_set.add(filter_to_toggle)

    # Ensure at least one filter is active
    if not filters_set:
        filters_set = {"НЦК", "НТП1", "НТП2"}

    return filters_to_string(filters_set)


def create_filters_row(
    menu: str, current_filters: str, page: int = 1
) -> List[InlineKeyboardButton]:
    """
    Создает строку кнопок для клавиатуры с фильтрами по направлению
    :param menu: Меню, для которого добавляется фильтр
    :param current_filters: Текущие активные фильтры
    :param page: Текущая открытая страница
    :return:
    """
    active_filters = parse_filters(current_filters)
    buttons = []

    # Для heads меню используем только НЦК и НТП2
    if menu == "heads":
        filter_options = [("НЦК", "НЦК"), ("НТП2", "НТП2")]
    else:
        filter_options = [("НЦК", "НЦК"), ("НТП1", "НТП1"), ("НТП2", "НТП2")]

    for display_name, filter_name in filter_options:
        is_active = filter_name in active_filters
        emoji = "✅" if is_active else "☑️"

        buttons.append(
            InlineKeyboardButton(
                text=f"{emoji} {display_name}",
                callback_data=SearchFilterToggleMenu(
                    menu=menu,
                    filter_name=filter_name,
                    page=page,
                    current_filters=current_filters,
                ).pack(),
            )
        )

    return buttons


def search_results_kb(
    users: list[Employee],
    page: int,
    total_pages: int,
    search_type: str,
    context: str = "mip",
    back_callback: str = "search",
    filters: str = "НЦК,НТП1,НТП2",
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
                callback_data=SearchUserResult(
                    user_id=user.user_id or user.id, context=context
                ).pack(),
            )
        )

    # Группируем кнопки по две в строке
    for i in range(0, len(user_buttons), 2):
        row = user_buttons[i : i + 2]
        buttons.append(row)

    # Пагинация (стиль shop_kb - 5 кнопок в строке)
    if total_pages > 1:
        from tgbot.keyboards.search.main import SearchMenu

        pagination_row = []

        # Первая кнопка (⏪ или пусто)
        if page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=SearchMenu(
                        menu=search_type, page=1, filters=filters
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Вторая кнопка (⬅️ или пусто)
        if page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=SearchMenu(
                        menu=search_type, page=page - 1, filters=filters
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Центральная кнопка - Индикатор страницы (всегда видна)
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
                    callback_data=SearchMenu(
                        menu=search_type, page=page + 1, filters=filters
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
                    callback_data=SearchMenu(
                        menu=search_type, page=total_pages, filters=filters
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Добавляем строку фильтров (после пагинации)
    filter_buttons = create_filters_row(search_type, filters, page)
    if filter_buttons:
        buttons.append(filter_buttons)

    # Кнопки "Назад" и "Домой"
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu=back_callback).pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="search").pack()
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def user_detail_kb(
    user: Employee,
    return_to: str = "search",
    head_id: int = 0,
    context: str = "mip",
    show_edit_buttons: bool = True,
    is_head: bool = False,
    head_user_id: int = 0,
    viewer_role: int = 1,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для детального просмотра пользователя

    :param user: Объект пользователя
    :param return_to: Куда возвращаться
    :param head_id: ID руководителя (если применимо)
    :param context: Контекст использования (mip, head)
    :param show_edit_buttons: Показывать ли кнопки редактирования
    :param is_head: Является ли пользователь руководителем
    :param head_user_id: ID пользователя-руководителя
    :param viewer_role: Роль пользователя, который смотрит информацию
    :return: Объект встроенной клавиатуры
    """
    buttons = []

    # Для ролей 1 и 3 показываем только базовые кнопки навигации
    if viewer_role in [1, 3]:
        # Кнопка назад
        if return_to == "search":
            back_callback = "search" if context == "mip" else "main"
        else:
            back_callback = return_to

        buttons.append(
            [
                InlineKeyboardButton(
                    text="↩️ Назад", callback_data=MainMenu(menu=back_callback).pack()
                ),
                InlineKeyboardButton(
                    text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
                ),
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    # Для роли 2 (руководители) показываем дополнительные кнопки
    elif viewer_role == 2:
        # Основные кнопки (расписание и KPI)
        action_buttons = [
            InlineKeyboardButton(
                text="📅 Расписание",
                callback_data=ViewUserSchedule(
                    user_id=user.user_id or user.id,
                    return_to=return_to,
                    head_id=head_id,
                    context=context,
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🌟 KPI",
                callback_data=ViewUserKPI(
                    user_id=user.user_id or user.id,
                    return_to=return_to,
                    head_id=head_id,
                    context=context,
                ).pack(),
            ),
        ]
        buttons.append(action_buttons)

        # Show edit buttons only if head can edit this user (not other heads)
        if show_edit_buttons:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="🟢 Казино" if user.is_casino_allowed else "🔴 Казино",
                        callback_data=HeadUserCasinoToggle(
                            user_id=user.user_id or user.id,
                            return_to=return_to,
                            head_id=head_id,
                            context=context,
                        ).pack(),
                    ),
                ]
            )
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="⚙️ Изменить статус",
                        callback_data=HeadUserStatusSelect(
                            user_id=user.user_id or user.id,
                            return_to=return_to,
                            head_id=head_id,
                            context=context,
                        ).pack(),
                    )
                ]
            )

    # Для остальных ролей (МИП и выше) показываем полную функциональность
    else:
        # Основные кнопки (расписание и KPI) - показываем всегда
        action_buttons = [
            InlineKeyboardButton(
                text="📅 Расписание",
                callback_data=ViewUserSchedule(
                    user_id=user.user_id or user.id,
                    return_to=return_to,
                    head_id=head_id,
                    context=context,
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🌟 KPI",
                callback_data=ViewUserKPI(
                    user_id=user.user_id or user.id,
                    return_to=return_to,
                    head_id=head_id,
                    context=context,
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
                        user_id=user.user_id, action="edit_fullname"
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="🛡️ Роль",
                    callback_data=EditUserMenu(
                        user_id=user.user_id, action="edit_role"
                    ).pack(),
                ),
            ]
            buttons.append(edit_buttons)
        elif show_edit_buttons and context == "head":
            # Only show edit buttons for heads if they can actually edit this user
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="🟢 Казино" if user.is_casino_allowed else "🔴 Казино",
                        callback_data=HeadUserCasinoToggle(
                            user_id=user.user_id or user.id,
                            return_to=return_to,
                            head_id=head_id,
                            context=context,
                        ).pack(),
                    ),
                ]
            )
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="⚙️ Изменить статус",
                        callback_data=HeadUserStatusSelect(
                            user_id=user.user_id or user.id,
                            return_to=return_to,
                            head_id=head_id,
                            context=context,
                        ).pack(),
                    )
                ]
            )

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
        # Приводим к title case для поиска в month_names
        current_month_title = current_month.lower().capitalize()
        current_month_idx = month_names.index(current_month_title) + 1

    except ValueError:
        # Если не найден в title case, попробуем найти по lowercase в русских месяцах
        from tgbot.misc.dicts import russian_months

        try:
            for idx, month_name in russian_months.items():
                if month_name.lower() == current_month.lower():
                    current_month_idx = idx
                    break
            else:
                current_month_idx = 1  # Дефолт к январю
        except Exception:
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

    # Получаем эмодзи для месяца
    month_emoji = MONTH_EMOJIS.get(current_month.lower(), "📅")

    nav_buttons.append(
        InlineKeyboardButton(
            text=f"{month_emoji} {current_month.capitalize()}",
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
    detail_text = "📋 Кратко" if is_detailed else "📄 Подробно"

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
                text="↩️ Назад",
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


def get_month_name_by_index(month_idx: int) -> str:
    """Получить название месяца по индексу"""
    from tgbot.misc.dicts import russian_months

    if 1 <= month_idx <= 12:
        return russian_months[month_idx]
    return "сентябрь"  # Возвращаем текущий месяц по умолчанию


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
    buttons = []

    # Основные кнопки KPI меню
    if current_action == "main":
        buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        text="🧮 Нормативы",
                        callback_data=ViewUserKPICalculator(
                            user_id=user_id,
                            return_to=return_to,
                            head_id=head_id,
                            context=context,
                        ).pack(),
                    ),
                    InlineKeyboardButton(
                        text="💰 Зарплата",
                        callback_data=ViewUserKPISalary(
                            user_id=user_id,
                            return_to=return_to,
                            head_id=head_id,
                            context=context,
                        ).pack(),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Обновить",
                        callback_data=ViewUserKPI(
                            user_id=user_id,
                            return_to=return_to,
                            head_id=head_id,
                            context=context,
                        ).pack(),
                    ),
                ],
            ]
        )
    elif current_action == "calculator":
        buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        text="🌟 Показатели",
                        callback_data=ViewUserKPI(
                            user_id=user_id,
                            return_to=return_to,
                            head_id=head_id,
                            context=context,
                        ).pack(),
                    ),
                    InlineKeyboardButton(
                        text="💰 Зарплата",
                        callback_data=ViewUserKPISalary(
                            user_id=user_id,
                            return_to=return_to,
                            head_id=head_id,
                            context=context,
                        ).pack(),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Обновить",
                        callback_data=ViewUserKPICalculator(
                            user_id=user_id,
                            return_to=return_to,
                            head_id=head_id,
                            context=context,
                        ).pack(),
                    ),
                ],
            ]
        )
    elif current_action == "salary":
        buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        text="🌟 Показатели",
                        callback_data=ViewUserKPI(
                            user_id=user_id,
                            return_to=return_to,
                            head_id=head_id,
                            context=context,
                        ).pack(),
                    ),
                    InlineKeyboardButton(
                        text="🧮 Нормативы",
                        callback_data=ViewUserKPICalculator(
                            user_id=user_id,
                            return_to=return_to,
                            head_id=head_id,
                            context=context,
                        ).pack(),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Обновить",
                        callback_data=ViewUserKPISalary(
                            user_id=user_id,
                            return_to=return_to,
                            head_id=head_id,
                            context=context,
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


def search_head_group_kb(
    head_id: int,
    members: list[Employee],
    page: int = 1,
    context: str = "mip",
    members_per_page: int = 8,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для отображения участников группы руководителя в поиске
    """
    from tgbot.keyboards.group.main import short_name

    buttons = []

    if not members:
        # Если нет участников, показываем только кнопки навигации
        buttons.append(
            [
                InlineKeyboardButton(
                    text="↩️ Назад",
                    callback_data=SearchUserResult(
                        user_id=head_id, context=context
                    ).pack(),
                )
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    # Рассчитываем пагинацию
    total_members = len(members)
    total_pages = (total_members + members_per_page - 1) // members_per_page

    # Рассчитываем диапазон участников для текущей страницы
    start_idx = (page - 1) * members_per_page
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
        trainee_emoji = "👶🏻 " if member.is_trainee else ""
        button_text = f"{status_emoji}{role_emoji}{trainee_emoji}{member_short_name}"

        row.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=SearchHeadGroupMemberDetail(
                    head_id=head_id,
                    member_id=member.user_id or member.id,
                    page=page,
                    context=context,
                ).pack(),
            )
        )

        # Второй участник в ряду (если есть)
        if i + 1 < len(page_members):
            member = page_members[i + 1]
            member_short_name = short_name(member.fullname)
            status_emoji = "🔒 " if not member.user_id else ""
            role_emoji = {3: "👮 ", 10: "🔨 "}.get(member.role, "")
            trainee_emoji = "👶🏻 " if member.is_trainee else ""
            button_text = (
                f"{status_emoji}{role_emoji}{trainee_emoji}{member_short_name}"
            )

            row.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=SearchHeadGroupMemberDetail(
                        head_id=head_id,
                        member_id=member.user_id or member.id,
                        page=page,
                        context=context,
                    ).pack(),
                )
            )

        buttons.append(row)

    # Добавляем пагинацию (только если больше одной страницы)
    if total_pages > 1:
        pagination_row = []

        # Первая кнопка (⏪ или пусто)
        if page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=SearchHeadGroupMembers(
                        head_id=head_id, page=1, context=context
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Вторая кнопка (⬅️ или пусто)
        if page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=SearchHeadGroupMembers(
                        head_id=head_id, page=page - 1, context=context
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Центральная кнопка - Индикатор страницы
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
                    callback_data=SearchHeadGroupMembers(
                        head_id=head_id, page=page + 1, context=context
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
                    callback_data=SearchHeadGroupMembers(
                        head_id=head_id, page=total_pages, context=context
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Добавляем кнопки навигации
    back_callback = "search" if context == "mip" else "main"
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=SearchUserResult(user_id=head_id, context=context).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой",
                callback_data=MainMenu(menu=back_callback).pack(),
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)

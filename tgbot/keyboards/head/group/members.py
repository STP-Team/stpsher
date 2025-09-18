from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import Sequence

from infrastructure.database.models.STP.employee import Employee
from tgbot.keyboards.user.main import MainMenu
from tgbot.misc.dicts import russian_months


def short_name(full_name: str) -> str:
    """Extract short name from full name."""
    # Remove date info in parentheses if present
    clean_name = full_name.split("(")[0].strip()
    parts = clean_name.split()

    if len(parts) >= 2:
        return " ".join(parts[:2])
    return clean_name


class HeadGroupMembersMenu(CallbackData, prefix="head_group_members"):
    menu: str = "members"
    page: int = 1


class HeadMemberDetailMenu(CallbackData, prefix="head_member_detail"):
    member_id: int
    page: int = 1


class HeadMemberActionMenu(CallbackData, prefix="head_member_action"):
    member_id: int
    action: str  # "schedule", "kpi", or "game_profile"
    page: int = 1


class HeadMemberScheduleMenu(CallbackData, prefix="head_member_schedule"):
    member_id: int
    month_idx: int = 0  # 0 = current month
    page: int = 1


class HeadMemberScheduleNavigation(CallbackData, prefix="head_member_sched_nav"):
    member_id: int
    action: str  # "prev_month", "next_month", "detailed", "compact"
    month_idx: int
    page: int = 1


class HeadMemberRoleChange(CallbackData, prefix="head_member_role"):
    member_id: int
    page: int = 1


class HeadMemberStatusSelect(CallbackData, prefix="head_member_status_select"):
    member_id: int
    page: int = 1


class HeadMemberStatusChange(CallbackData, prefix="head_member_status_change"):
    member_id: int
    status_type: str  # "trainee" or "duty"
    page: int = 1


class HeadMemberKPIMenu(CallbackData, prefix="head_member_kpi"):
    member_id: int
    action: str  # "main", "calculator", "salary"
    page: int = 1


class HeadMemberGameProfileMenu(CallbackData, prefix="head_member_game_profile"):
    member_id: int
    page: int = 1


class HeadMemberGameHistoryMenu(CallbackData, prefix="head_member_game_history"):
    member_id: int
    history_page: int = 1
    page: int = 1


class HeadMemberTransactionDetailMenu(
    CallbackData, prefix="head_member_transaction_detail"
):
    member_id: int
    transaction_id: int
    history_page: int = 1
    page: int = 1


def head_group_members_kb(
    members: Sequence[Employee],
    current_page: int = 1,
    members_per_page: int = 8,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для отображения участников группы с пагинацией.
    Отображает 2 участника в ряд, по умолчанию 8 участников на страницу (4 ряда).
    """
    buttons = []

    if not members:
        # Если нет участников, показываем только кнопки навигации
        buttons.append(
            [
                InlineKeyboardButton(
                    text="↩️ Назад",
                    callback_data=MainMenu(menu="group_management").pack(),
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
        trainee_emoji = "👶🏻 " if member.is_trainee else ""
        button_text = f"{status_emoji}{role_emoji}{trainee_emoji}{member_short_name}"

        row.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=HeadMemberDetailMenu(
                    member_id=member.id, page=current_page
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
                    callback_data=HeadMemberDetailMenu(
                        member_id=member.id, page=current_page
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
                    callback_data=HeadGroupMembersMenu(menu="members", page=1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Вторая кнопка (⬅️ или пусто)
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=HeadGroupMembersMenu(
                        menu="members", page=current_page - 1
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
                    callback_data=HeadGroupMembersMenu(
                        menu="members", page=current_page + 1
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
                    callback_data=HeadGroupMembersMenu(
                        menu="members", page=total_pages
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
                callback_data=MainMenu(menu="group_management").pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def head_member_detail_kb(
    member_id: int, page: int = 1, member_role: int = None
) -> InlineKeyboardMarkup:
    """
    Клавиатура для детального просмотра участника группы
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="📅 График",
                callback_data=HeadMemberActionMenu(
                    member_id=member_id, action="schedule", page=page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🌟 Показатели",
                callback_data=HeadMemberKPIMenu(
                    member_id=member_id, action="main", page=page
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🏮 Игровой профиль",
                callback_data=HeadMemberActionMenu(
                    member_id=member_id, action="game_profile", page=page
                ).pack(),
            ),
        ],
    ]

    # Добавляем кнопку смены статуса только для специалистов (роль 1) и дежурных (роль 3)
    if member_role in [1, 3]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="⚙️ Изменить",
                    callback_data=HeadMemberStatusSelect(
                        member_id=member_id, page=page
                    ).pack(),
                ),
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=HeadGroupMembersMenu(menu="members", page=page).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_month_name_by_index(month_idx: int) -> str:
    """Получить название месяца по индексу"""
    if 1 <= month_idx <= 12:
        return russian_months[month_idx]
    return "Текущий месяц"


def head_member_schedule_kb(
    member_id: int, current_month: str, page: int = 1, is_detailed: bool = False
) -> InlineKeyboardMarkup:
    """
    Клавиатура для просмотра расписания участника группы с навигацией по месяцам
    """
    # Получаем индекс текущего месяца
    current_month_idx = 1
    for month_idx, month_name in russian_months.items():
        if month_name == current_month:
            current_month_idx = month_idx
            break

    buttons = []

    # Навигация по месяцам
    month_nav_row = []

    # Предыдущий месяц
    prev_month_idx = current_month_idx - 1 if current_month_idx > 1 else 12
    month_nav_row.append(
        InlineKeyboardButton(
            text="⬅️",
            callback_data=HeadMemberScheduleNavigation(
                member_id=member_id,
                action="prev_month",
                month_idx=prev_month_idx,
                page=page,
            ).pack(),
        )
    )

    # Текущий месяц (индикатор) - нормализуем название с заглавной буквы
    month_display = current_month.capitalize()
    month_nav_row.append(
        InlineKeyboardButton(
            text=f"📅 {month_display}",
            callback_data="noop",
        )
    )

    # Следующий месяц
    next_month_idx = current_month_idx + 1 if current_month_idx < 12 else 1
    month_nav_row.append(
        InlineKeyboardButton(
            text="➡️",
            callback_data=HeadMemberScheduleNavigation(
                member_id=member_id,
                action="next_month",
                month_idx=next_month_idx,
                page=page,
            ).pack(),
        )
    )

    buttons.append(month_nav_row)

    # Переключение детального/компактного вида
    view_toggle_text = "📋 Компактно" if is_detailed else "📄 Подробно"
    view_action = "compact" if is_detailed else "detailed"

    buttons.append(
        [
            InlineKeyboardButton(
                text=view_toggle_text,
                callback_data=HeadMemberScheduleNavigation(
                    member_id=member_id,
                    action=view_action,
                    month_idx=current_month_idx,
                    page=page,
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

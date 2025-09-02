from typing import List, Set

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class GokLevelingMenu(CallbackData, prefix="gok_leveling"):
    menu: str
    page: int = 1
    filters: str = "НЦК,НТП"  # Фильтры по направлению


class GokFilterToggleMenu(CallbackData, prefix="gok_filter_toggle"):
    menu: str  # "achievements_all" или "awards_all"
    filter_name: str  # "НЦК" или "НТП"
    page: int = 1
    current_filters: str = "НЦК,НТП"  # текущие активные фильтры


class GokAwardsMenu(CallbackData, prefix="gok_awards"):
    menu: str
    page: int = 1
    award_id: int = 0
    filters: str = "НЦК,НТП"  # comma-separated active filters


class GokAwardActivationMenu(CallbackData, prefix="gok_award_activation"):
    user_award_id: int
    page: int = 1


class GokAwardActionMenu(CallbackData, prefix="gok_award_action"):
    user_award_id: int
    action: str  # "approve" or "reject"
    page: int = 1


def parse_filters(filters_str: str) -> Set[str]:
    """
    Парсит фильтры
    :param filters_str: Список фильтров
    :return:
    """
    if not filters_str:
        return {"НЦК", "НТП"}
    return set(
        filter_name.strip()
        for filter_name in filters_str.split(",")
        if filter_name.strip()
    )


def filters_to_string(filters_set: Set[str]) -> str:
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
        filters_set = {"НЦК", "НТП"}

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

    filter_options = [("НЦК", "НЦК"), ("НТП", "НТП")]

    for display_name, filter_name in filter_options:
        is_active = filter_name in active_filters
        emoji = "✅" if is_active else "☑️"

        buttons.append(
            InlineKeyboardButton(
                text=f"{emoji} {display_name}",
                callback_data=GokFilterToggleMenu(
                    menu=menu,
                    filter_name=filter_name,
                    page=page,
                    current_filters=current_filters,
                ).pack(),
            )
        )

    return buttons


def gok_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура меню ГОК для достижений и наград
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✍️ Награды для активации",
                callback_data=GokLevelingMenu(menu="awards_activation").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🎯 Достижения",
                callback_data=GokLevelingMenu(menu="achievements_all").pack(),
            ),
            InlineKeyboardButton(
                text="👏 Награды",
                callback_data=GokAwardsMenu(menu="awards_all").pack(),
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard

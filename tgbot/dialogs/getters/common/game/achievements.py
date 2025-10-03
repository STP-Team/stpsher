"""Геттеры для списка достижений."""

from typing import Dict

from aiogram_dialog import DialogManager

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.dialogs.filters.common.game_filters import (
    get_position_callback_key,
    get_position_display_name,
    get_position_from_callback,
)
from tgbot.dialogs.getters.user.game.achievements import achievements_getter


async def role_based_achievements_filter_getter(
    user: Employee, stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **kwargs
) -> Dict[str, str]:
    """Фильтрует список достижений.

    Фильтр зависит от:
    - роли пользователя
    - выбранных фильтров

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь отфильтрованных достижений
    """
    # Определяем роли
    is_manager = user.role in [5, 6]  # ГОК и МИП
    is_user = user.role in [1, 3]  # Специалисты и дежурные
    user_division = "НЦК" if "НЦК" in user.division else "НТП"

    # Загружаем достижения в зависимости от роли
    if is_manager:
        base_data = await achievements_getter(stp_repo=stp_repo, **kwargs)
    elif is_user:
        base_data = await achievements_getter(
            stp_repo=stp_repo, division=user_division, **kwargs
        )
    else:
        base_data = await achievements_getter(**kwargs)

    all_achievements = base_data["achievements"]

    # Фильтруем достижения по подразделению для специалистов
    if is_user:
        if "НТП1" in user.division:
            allowed_positions = [
                "Специалист первой линии",
                "Ведущий специалист первой линии",
            ]
            achievements = [
                ach for ach in all_achievements if ach[4] in allowed_positions
            ]
        elif "НТП2" in user.division:
            allowed_positions = [
                "Специалист второй линии",
                "Ведущий специалист второй линии",
                "Эксперт второй линии",
            ]
            achievements = [
                ach for ach in all_achievements if ach[4] in allowed_positions
            ]
        else:
            achievements = all_achievements
    else:
        achievements = all_achievements

    # Извлекаем уникальные позиции
    positions = {achievement[4] for achievement in achievements}

    # Создаем данные для радио-кнопок
    position_radio_data = []
    if is_user:
        position_radio_data = [
            (get_position_callback_key(pos), get_position_display_name(pos))
            for pos in positions
        ]
        position_radio_data.insert(0, ("all", "Все"))

    division_radio_data = [("all", "Все"), ("nck", "НЦК"), ("ntp", "НТП")]
    period_radio_data = [("all", "Все"), ("d", "День"), ("w", "Неделя"), ("m", "Месяц")]

    # Получаем текущие фильтры
    if is_user:
        selected_filter = dialog_manager.dialog_data.setdefault(
            "achievement_position_filter", "all"
        )
    else:
        selected_filter = dialog_manager.dialog_data.setdefault(
            "achievement_division_filter", "all"
        )

    selected_period = dialog_manager.dialog_data.setdefault(
        "achievement_period_filter", "all"
    )

    # Фильтруем достижения по выбранному фильтру
    filtered_achievements = achievements

    if is_user and selected_filter != "all":
        # Фильтр по позиции для обычных пользователей
        actual_position = get_position_from_callback(selected_filter)
        filtered_achievements = [a for a in achievements if a[4] == actual_position]
    elif is_manager and selected_filter != "all":
        # Фильтр по подразделению для руководителей
        division_map = {"nck": "НЦК", "ntp": "НТП"}
        if selected_filter in division_map:
            filtered_achievements = [
                a for a in achievements if a[6] == division_map[selected_filter]
            ]

    # Фильтруем по периоду
    if selected_period != "all" and stp_repo:
        # Определяем параметры запроса для периода
        if is_manager:
            division_param = (
                "НЦК"
                if selected_filter == "nck"
                else "НТП"
                if selected_filter == "ntp"
                else None
            )
            original_data = await stp_repo.achievement.get_achievements(
                division=division_param
            )
        else:
            original_data = await stp_repo.achievement.get_achievements(
                division=user_division
            )

        period_map = {ach.id: ach.period for ach in original_data}
        filtered_achievements = [
            a for a in filtered_achievements if period_map.get(a[0]) == selected_period
        ]

    # Формируем результат
    result = {
        "achievements": filtered_achievements,
        "period_radio_data": period_radio_data,
        "achievement_period_filter": selected_period,
        "checked_period": selected_period,
        "position_radio_data": position_radio_data,
        "division_radio_data": division_radio_data,
    }

    # Добавляем специфичные для роли данные
    if is_user:
        result.update(
            {
                "achievement_position_filter": selected_filter,
                "checked": selected_filter,
            }
        )
    else:
        result.update(
            {
                "achievement_division_filter": selected_filter,
                "checked": selected_filter,
            }
        )

    return result

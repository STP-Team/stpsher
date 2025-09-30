from tgbot.dialogs.filters.common.game_filters import (
    get_position_callback_key,
    get_position_display_name,
    get_position_from_callback,
)
from tgbot.dialogs.getters.user.game.achievements import achievements_getter


async def role_based_achievements_filter_getter(**kwargs):
    """
    Фильтрует достижения в зависимости от роли пользователя и выбранных фильтров
    """
    dialog_manager = kwargs.get("dialog_manager")
    user = kwargs.get("user")
    is_user_role = user and user.role == 1

    # Определяем параметры для загрузки достижений в зависимости от роли
    if user and user.role == 6:  # GOK role
        # Для GOK показываем все достижения из всех подразделений
        base_data = await achievements_getter(**kwargs)
    else:
        # Для специалистов (role 1 или 3) показываем достижения своего подразделения
        # Передаем division пользователя в базовый getter
        base_data = await achievements_getter(
            division="НЦК" if user and "НЦК" in user.division else "НТП", **kwargs
        )

    # Получаем все достижения для определения доступных позиций
    all_achievements = base_data["achievements"]

    # Фильтруем достижения по роли пользователя
    if user:
        if user.role == 6:  # GOK role
            # Показываем все достижения без фильтрации по подразделению
            achievements = all_achievements
        elif user.role in [1, 3]:  # Specialist roles
            # Фильтруем по подразделению как раньше
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
    else:
        achievements = all_achievements

    # Извлекаем уникальные позиции из отфильтрованных достижений
    positions = set()
    for achievement in achievements:
        positions.add(achievement[4])

    # Создаем данные для радио-кнопок позиций (только для обычных пользователей)
    position_radio_data = []
    if is_user_role:
        for pos in list(positions):
            callback_key = get_position_callback_key(pos)
            display_name = get_position_display_name(pos)
            position_radio_data.append((callback_key, display_name))
        position_radio_data.insert(0, ("all", "Все"))

    # Создаем данные для радио-кнопок подразделений (для руководителей)
    division_radio_data = [
        ("all", "Все"),
        ("nck", "НЦК"),
        ("ntp", "НТП"),
    ]

    # Создаем данные для радио-кнопок периодов
    period_radio_data = [
        ("all", "Все"),
        ("d", "День"),
        ("w", "Неделя"),
        ("m", "Месяц"),
    ]

    # Проверяем текущий выбор фильтра позиции/подразделения
    if is_user_role:
        selected_filter = dialog_manager.dialog_data.get(
            "achievement_position_filter", "all"
        )
        if "achievement_position_filter" not in dialog_manager.dialog_data:
            dialog_manager.dialog_data["achievement_position_filter"] = "all"
            selected_filter = "all"
    else:
        selected_filter = dialog_manager.dialog_data.get(
            "achievement_division_filter", "all"
        )
        if "achievement_division_filter" not in dialog_manager.dialog_data:
            dialog_manager.dialog_data["achievement_division_filter"] = "all"
            selected_filter = "all"

    # Проверяем текущий выбор фильтра периода
    selected_period = dialog_manager.dialog_data.get("achievement_period_filter", "all")

    if "achievement_period_filter" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["achievement_period_filter"] = "all"
        selected_period = "all"

    # Фильтруем достижения по выбранному фильтру
    if is_user_role:
        # Фильтр по позиции для обычных пользователей
        if selected_filter == "all":
            filtered_achievements = achievements
        else:
            actual_position = get_position_from_callback(selected_filter)
            filtered_achievements = [a for a in achievements if a[4] == actual_position]
    else:
        # Фильтр по подразделению для руководителей
        if selected_filter == "all":
            filtered_achievements = achievements
        elif selected_filter == "nck":
            filtered_achievements = [
                a
                for a in achievements
                if a[6] == "НЦК"  # a[6] это division
            ]
        elif selected_filter == "ntp":
            filtered_achievements = [
                a
                for a in achievements
                if a[6] == "НТП"  # a[6] это division
            ]
        else:
            filtered_achievements = achievements

    # Дополнительно фильтруем по периоду
    if selected_period != "all":
        stp_repo = kwargs.get("stp_repo")
        user = kwargs.get("user")

        if stp_repo and user:
            # Для GOK получаем все достижения, для остальных - по подразделению
            if user.role == 6:
                original_data = await stp_repo.achievement.get_achievements()
            else:
                normalized_division = "НЦК" if "НЦК" in user.division else "НТП"
                original_data = await stp_repo.achievement.get_achievements(
                    division=normalized_division
                )

            period_map = {ach.id: ach.period for ach in original_data}

            filtered_achievements = [
                a
                for a in filtered_achievements
                if period_map.get(a[0]) == selected_period
            ]

    result = {
        "achievements": filtered_achievements,
        "period_radio_data": period_radio_data,
        "achievement_period_filter": selected_period,
        "checked_period": selected_period,
        "position_radio_data": position_radio_data,  # Always provide, even if empty
        "division_radio_data": division_radio_data,  # Always provide
    }

    # Добавляем данные в зависимости от роли
    if is_user_role:
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

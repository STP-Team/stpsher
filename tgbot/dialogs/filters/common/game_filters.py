from tgbot.dialogs.getters.user.game.achievements import user_achievements_getter
from tgbot.dialogs.getters.user.game.shop import products_getter


def get_position_display_name(position: str) -> str | None:
    """Возвращает отображаемое имя для позиции"""
    match position:
        case "Специалист":
            return "Спец"
        case "Специалист первой линии":
            return "Спец"
        case "Специалист второй линии":
            return "Спец"
        case "Ведущий специалист":
            return "Ведущий"
        case "Ведущий специалист первой линии":
            return "Ведущий"
        case "Ведущий специалист второй линии":
            return "Ведущий"
        case "Эксперт":
            return "Эксперт"
        case "Эксперт второй линии":
            return "Эксперт"
        case _:
            return position


def get_position_callback_key(position: str) -> str:
    """Возвращает ключ для callback без русских символов"""
    match position:
        case "Специалист":
            return "spec"
        case "Специалист первой линии":
            return "spec_ntp1"
        case "Специалист второй линии":
            return "spec_ntp2"
        case "Ведущий специалист":
            return "lead_spec"
        case "Ведущий специалист первой линии":
            return "lead_spec_ntp1"
        case "Ведущий специалист второй линии":
            return "lead_spec_ntp2"
        case "Эксперт":
            return "expert"
        case "Эксперт второй линии":
            return "expert_ntp2"
        case _:
            return position.lower().replace(" ", "_")


def get_position_from_callback(callback_key: str) -> str:
    """Возвращает оригинальную позицию по ключу callback"""
    match callback_key:
        case "spec":
            return "Специалист"
        case "spec_ntp1":
            return "Специалист первой линии"
        case "spec_ntp2":
            return "Специалист второй линии"
        case "lead_spec":
            return "Ведущий специалист"
        case "lead_spec_ntp1":
            return "Ведущий специалист первой линии"
        case "lead_spec_ntp2":
            return "Ведущий специалист второй линии"
        case "expert":
            return "Эксперт"
        case "expert_ntp2":
            return "Эксперт второй линии"
        case _:
            return callback_key


async def product_filter_getter(**kwargs):
    """
    Фильтрует предметы в зависимости от выбранного радио-фильтра
    """
    base_data = await products_getter(**kwargs)
    dialog_manager = kwargs.get("dialog_manager")

    # Проверяем текущий выбор фильтра (стандартно на 'Доступные')
    filter_type = dialog_manager.dialog_data.get("product_filter", "available")

    # Устанавливаем стандартный фильтр если не установлено иное
    if "product_filter" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["product_filter"] = "available"

    products = base_data["products"]
    user_balance = base_data["user_balance"]

    if filter_type == "available":
        # Фильтруем предметы, доступные пользователю
        filtered_products = [
            p for p in products if p[4] <= user_balance
        ]  # p[4] это стоимость
    else:  # "Все предметы"
        filtered_products = products

    return {
        "products": filtered_products,
        "user_balance": user_balance,
        "product_filter": filter_type,
    }


async def achievements_filter_getter(**kwargs):
    """
    Фильтрует достижения в зависимости от выбранной позиции и периода
    """
    base_data = await user_achievements_getter(**kwargs)
    dialog_manager = kwargs.get("dialog_manager")

    # Получаем все достижения для определения доступных позиций
    all_achievements = base_data["achievements"]

    # Получаем информацию о пользователе для фильтрации
    user = kwargs.get("user")

    # Фильтруем достижения по подразделению пользователя
    if user:
        if "НТП1" in user.division:
            # Показываем только достижения для первой линии
            allowed_positions = [
                "Специалист первой линии",
                "Ведущий специалист первой линии",
            ]
            achievements = [
                ach
                for ach in all_achievements
                if ach[4] in allowed_positions  # ach[4] это position
            ]
        elif "НТП2" in user.division:
            # Показываем только достижения для второй линии
            allowed_positions = [
                "Специалист второй линии",
                "Ведущий специалист второй линии",
                "Эксперт второй линии",
            ]
            achievements = [
                ach
                for ach in all_achievements
                if ach[4] in allowed_positions  # ach[4] это position
            ]
        else:
            # Для остальных подразделений показываем все достижения
            achievements = all_achievements
    else:
        achievements = all_achievements

    # Извлекаем уникальные позиции из отфильтрованных достижений
    positions = set()
    for achievement in achievements:
        positions.add(achievement[4])  # achievement[4] это position

    # Создаем данные для радио-кнопок позиций с callback-безопасными ключами
    position_radio_data = []
    for pos in list(positions):
        callback_key = get_position_callback_key(pos)
        display_name = get_position_display_name(pos)
        position_radio_data.append((callback_key, display_name))

    # Добавляем опцию "Все" в начало
    position_radio_data.insert(0, ("all", "Все"))

    # Создаем данные для радио-кнопок периодов
    period_radio_data = [
        ("all", "Все"),
        ("d", "День"),
        ("w", "Неделя"),
        ("m", "Месяц"),
    ]

    # Проверяем текущий выбор фильтра позиции (стандартно на 'all')
    selected_position = dialog_manager.dialog_data.get(
        "achievement_position_filter", "all"
    )

    # Проверяем текущий выбор фильтра периода (стандартно на 'all')
    selected_period = dialog_manager.dialog_data.get("achievement_period_filter", "all")

    # Устанавливаем стандартные фильтры если не установлено иное
    if "achievement_position_filter" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["achievement_position_filter"] = "all"
        selected_position = "all"

    if "achievement_period_filter" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["achievement_period_filter"] = "all"
        selected_period = "all"

    # Фильтруем достижения по выбранной позиции
    if selected_position == "all":
        filtered_achievements = achievements
    else:
        # Конвертируем callback key обратно в оригинальную позицию для фильтрации
        actual_position = get_position_from_callback(selected_position)
        filtered_achievements = [
            a
            for a in achievements
            if a[4] == actual_position  # a[4] это position
        ]

    # Дополнительно фильтруем по периоду
    if selected_period != "all":
        # Нужно получить оригинальные данные для фильтрации по периоду
        # achievement[5] содержит отформатированный период, но нам нужен оригинальный
        stp_repo = kwargs.get("stp_repo")
        user = kwargs.get("user")

        if stp_repo and user:
            # Нормализуем division как в user_achievements_getter
            normalized_division = "НЦК" if "НЦК" in user.division else "НТП"
            original_data = await stp_repo.achievement.get_achievements(
                division=normalized_division
            )
            # Создаем словарь для быстрого поиска периода по ID
            period_map = {ach.id: ach.period for ach in original_data}

            # Фильтруем по периоду
            filtered_achievements = [
                a
                for a in filtered_achievements
                if period_map.get(a[0]) == selected_period  # a[0] это ID достижения
            ]

    return {
        "achievements": filtered_achievements,
        "position_radio_data": position_radio_data,
        "period_radio_data": period_radio_data,
        "achievement_position_filter": selected_position,
        "achievement_period_filter": selected_period,
        "checked": selected_position,  # Explicit checked state for Position Radio
        "checked_period": selected_period,  # Explicit checked state for Period Radio
    }

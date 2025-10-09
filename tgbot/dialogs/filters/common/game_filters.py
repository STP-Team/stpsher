"""Фильтры для игровых меню."""

from typing import Any, Dict

from aiogram_dialog import DialogManager

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.dialogs.getters.common.game.shop import products_getter
from tgbot.dialogs.getters.user.game.achievements import (
    achievements_getter,
    user_achievements_getter,
)


def get_position_display_name(position: str) -> str:
    """Возвращает отображаемое название для позиции для фильтров.

    Args:
        position: Должность сотрудника

    Returns:
        Сокращенное название должности
    """
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
    """Возвращает ключ для callback без русских символов.

    TODO необходимо проверить нужна ли эта функция

    Args:
        position: Должность сотрудника

    Returns:
        Ключ должности для callback
    """
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
    """Возвращает оригинальную позицию по ключу callback.

    Args:
        callback_key: Ключ callback

    Returns:
        Оригинальное название должности
    """
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


async def product_filter_getter(
    dialog_manager: DialogManager, user: Employee, stp_repo: MainRequestsRepo, **kwargs
) -> dict[str, list[Any] | str | Any]:
    """Фильтрует предметы в зависимости от выбранного фильтра.

    Args:
        dialog_manager: Менеджер диалога
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь предметов с активным фильтром и балансом пользователя
    """
    # Определяем роль пользователя
    is_user = user.role in [1, 3]  # Специалисты и дежурные
    is_manager = user.role in [2, 5, 6]  # ГОК и МИП

    # TODO Исправить некорректное отображение списка предметов у менеджеров при фильтрации перед комитом
    # Для менеджеров получаем выбранное подразделение
    division_param = None
    if is_manager:
        selected_division = dialog_manager.find("product_division_filter").get_checked()
        if selected_division != "all":
            division_map = {"nck": "НЦК", "ntp": "НТП"}
            division_param = division_map.get(selected_division, "")

            # Загружаем продукты с учетом фильтра подразделения
            base_data = await products_getter(
                user=user, stp_repo=stp_repo, division=division_param, **kwargs
            )
        else:
            base_data = await products_getter(user=user, stp_repo=stp_repo, **kwargs)

    products = base_data["products"]
    user_balance = base_data["user_balance"]

    # Для обычных пользователей фильтруем по доступности (стоимости)
    if is_user:
        filter_type = dialog_manager.find("product_filter").get_checked()

        if filter_type == "available":
            # Фильтруем предметы, доступные пользователю по балансу
            filtered_products = [
                p for p in products if p[4] <= user_balance
            ]  # p[4] это стоимость
        else:  # "Все предметы"
            filtered_products = products
    else:
        # Для менеджеров показываем все предметы (фильтр уже применен при загрузке)
        filtered_products = products
        filter_type = None

    # Данные для радио-кнопок подразделений (для менеджеров)
    division_radio_data = [("all", "Все"), ("nck", "НЦК"), ("ntp", "НТП")]

    result = {
        "products": filtered_products,
        "user_balance": user_balance,
        "is_user": is_user,
        "division_radio_data": division_radio_data,
    }

    # Добавляем специфичные для роли данные
    if is_user:
        result["product_filter"] = filter_type
    else:
        result["product_division_filter"] = dialog_manager.find(
            "product_division_filter"
        ).get_checked()

    return result


async def achievements_filter_getter(
    user: Employee, stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **kwargs
) -> Dict[str, list[Any] | str | Any]:
    """Фильтрует достижения в зависимости от выбранной позиции и периода.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь доступных достижений с фильтрацией по направлению
    """
    # Определяем роль пользователя
    is_user = user.role in [1, 3]
    if not is_user:
        base_data = await achievements_getter(stp_repo=stp_repo, **kwargs)
    else:
        base_data = await user_achievements_getter(
            user=user, stp_repo=stp_repo, **kwargs
        )

    # Получаем все достижения для определения доступных позиций
    all_achievements = base_data["achievements"]

    # Фильтруем достижения по подразделению пользователя
    if is_user:
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

    # Данные для радио-кнопок подразделений (для менеджеров)
    division_radio_data = [("all", "Все"), ("nck", "НЦК"), ("ntp", "НТП")]

    # Проверяем текущий выбор фильтра позиции (для пользователей)
    selected_position = dialog_manager.find("achievement_position_filter").get_checked()

    # Проверяем текущий выбор фильтра подразделения (для менеджеров)
    selected_division = dialog_manager.find("achievement_division_filter").get_checked()

    # Проверяем текущий выбор фильтра периода
    selected_period = dialog_manager.find("achievement_period_filter").get_checked()

    # Фильтруем достижения по выбранному фильтру в зависимости от роли
    if is_user:
        # Для пользователей фильтруем по позиции
        if selected_position == "all":
            filtered_achievements = achievements
        else:
            # Конвертируем callback key обратно в оригинальную позицию для фильтрации
            actual_position = get_position_from_callback(selected_position)
            filtered_achievements = [
                ach
                for ach in achievements
                if ach[4] == actual_position  # a[4] это position
            ]
    else:
        # Для менеджеров фильтруем по подразделению
        if selected_division == "all":
            filtered_achievements = achievements
        else:
            # Конвертируем callback key в название подразделения
            division_map = {"nck": "НЦК", "ntp": "НТП"}
            actual_division = division_map.get(selected_division, "")
            filtered_achievements = [a for a in achievements if a[6] == actual_division]

    # Дополнительно фильтруем по периоду
    if selected_period != "all":
        # Нужно получить оригинальные данные для фильтрации по периоду
        # achievement[5] содержит отформатированный период, но нам нужен оригинальный

        if stp_repo:
            # Для менеджеров используем выбранное подразделение, для пользователей - их подразделение
            if not is_user:
                if selected_division != "all":
                    division_map = {"nck": "НЦК", "ntp": "НТП"}
                    normalized_division = division_map.get(selected_division)
                else:
                    normalized_division = None
            else:
                normalized_division = "НЦК" if "НЦК" in user.division else "НТП"

            original_data = await stp_repo.achievement.get_achievements(
                division=normalized_division
            )
            # Создаем словарь для быстрого поиска периода по ID
            period_map = {ach.id: ach.period for ach in original_data}

            # Фильтруем по периоду
            filtered_achievements = [
                ach
                for ach in filtered_achievements
                if period_map.get(ach[0]) == selected_period
            ]

    return {
        "is_user": is_user,
        "achievements": filtered_achievements,
        "position_radio_data": position_radio_data,
        "period_radio_data": period_radio_data,
        "division_radio_data": division_radio_data,
        "achievement_position_filter": selected_position,
        "achievement_division_filter": selected_division,
        "achievement_period_filter": selected_period,
        "checked": selected_position,
        "checked_period": selected_period,
    }

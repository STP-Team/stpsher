"""Геттеры для функций поиска."""

from html import escape
from typing import Any, Sequence

from aiogram_dialog import DialogManager
from sqlalchemy.orm import Mapped
from stp_database import Employee, MainRequestsRepo
from stp_database.repo.KPI.requests import KPIRequestsRepo

from tgbot.dialogs.getters.common.game.kpi import (
    kpi_getter,
    kpi_requirements_getter,
    salary_getter,
)
from tgbot.dialogs.getters.common.schedules import user_schedule_getter
from tgbot.misc.dicts import roles
from tgbot.misc.helpers import format_fullname, get_role, get_status_emoji


async def search_getter(
    stp_repo: MainRequestsRepo, **_kwargs
) -> dict[str, Sequence[Employee] | None | int]:
    """Геттер для главного меню поиска.

    Args:
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь специалистов и руководителей
    """
    specialists = await stp_repo.employee.get_users(roles=[1, 3])
    total_specialists = len(specialists)

    heads = await stp_repo.employee.get_users(roles=2)
    total_heads = len(heads)

    return {
        "specialists": specialists,
        "total_specialists": total_specialists,
        "heads": heads,
        "total_heads": total_heads,
    }


async def search_specialists_getter(
    dialog_manager: DialogManager, **kwargs
) -> dict[
    str, list[Any] | list[tuple[Mapped[str], Mapped[str]] | tuple[str, str]] | str | int
]:
    """Геттер для меню поиска специалистов.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь отфильтрованного списка специалистов
    """
    base_data = await search_getter(**kwargs)
    specialists = base_data.get("specialists")

    selected_division = dialog_manager.find("search_divisions").get_checked()

    # Фильтруем руководителей по направлению если выбран фильтр
    if selected_division != "all":
        specialists = [s for s in specialists if s.division == selected_division]

    sorted_specialists = sorted(specialists, key=lambda k: k.fullname)

    formatted_specialists = []
    for specialist in sorted_specialists:
        role_info = get_role(specialist.role)
        formatted_specialists.append((
            specialist.id,
            format_fullname(specialist.fullname, True, True),
            role_info["emoji"],
        ))

    # Получаем все уникальные направления специалистов
    all_specialists = base_data.get("specialists")
    divisions = list(set(s.division for s in all_specialists if s.division))
    divisions.sort()

    # Добавляем доступные направления в качестве фильтра
    division_options = [("all", "Все")] + [(div, div) for div in divisions]

    return {
        **base_data,
        "specialists_list": formatted_specialists,
        "division_options": division_options,
        "selected_division": selected_division,
        "total_specialists": len(formatted_specialists),
    }


async def search_heads_getter(
    dialog_manager: DialogManager, **kwargs
) -> dict[
    str, list[Any] | list[tuple[Mapped[str], Mapped[str]] | tuple[str, str]] | str | int
]:
    """Геттер для меню поиска руководителей.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь отфильтрованного списка руководителей
    """
    base_data = await search_getter(**kwargs)
    all_heads = base_data.get("heads")

    selected_division = dialog_manager.find("search_divisions").get_checked()

    # Фильтруем руководителей по направлению если выбран фильтр
    if selected_division != "all":
        all_heads = [s for s in all_heads if s.division == selected_division]

    sorted_heads = sorted(all_heads, key=lambda k: k.fullname)

    formatted_heads = []
    for head in sorted_heads:
        role_info = get_role(head.role)
        formatted_heads.append((
            head.id,
            format_fullname(head.fullname, True, True),
            role_info["emoji"],
        ))

    # Получаем все уникальные направления руководителей
    all_heads = base_data.get("heads")
    divisions = list(set(s.division for s in all_heads if s.division))
    divisions.sort()

    # Добавляем доступные направления в качестве фильтра
    division_options = [("all", "Все")] + [(div, div) for div in divisions]

    return {
        **base_data,
        "heads_list": formatted_heads,
        "division_options": division_options,
        "selected_division": selected_division,
        "total_heads": len(formatted_heads),
    }


async def search_results_getter(
    dialog_manager: DialogManager, **_kwargs
) -> dict[str, str]:
    """Геттер для получения результатов поиска сотрудников.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с найденными сотрудниками по запросу
    """
    search_results = dialog_manager.dialog_data.get("search_results", [])
    search_query = dialog_manager.dialog_data.get("search_query", "")
    total_found = dialog_manager.dialog_data.get("total_found", 0)

    return {
        "search_results": search_results,
        "search_query": search_query,
        "total_found": total_found,
    }


async def search_user_info_getter(
    user: Employee,
    stp_repo: MainRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> (
    dict[str, str]
    | dict[str, Employee | Sequence[Employee] | None | bool | Mapped[bool]]
    | dict[str, str | bool]
):
    """Геттер для получения информации о выбранном пользователе.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с информацией о выбранном сотруднике
    """
    selected_user_id = dialog_manager.dialog_data.get("selected_user_id")
    is_head = user.role == 2
    is_duty = user.role == 3
    is_mip = user.role == 6
    is_root = user.role == 10

    if not selected_user_id:
        return {"user_info": "❌ Пользователь не выбран"}

    try:
        # Получаем информацию о пользователе
        searched_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))
        if not searched_user:
            return {"user_info": "❌ Пользователь не найден"}

        # Получаем руководителя если есть
        user_head = None
        if searched_user.head:
            user_head = await stp_repo.employee.get_users(fullname=searched_user.head)

        user_info = f"""<b>{format_fullname(searched_user.fullname, False, True, searched_user.username, searched_user.user_id)}</b>

<b>💼 Должность:</b> {searched_user.position} {searched_user.division}"""

        if user_head:
            user_info += f"\n<b>👑 Руководитель:</b> {
                format_fullname(
                    user_head.fullname,
                    True,
                    True,
                    user_head.username,
                    user_head.user_id,
                )
            }"

        if searched_user.email:
            user_info += f"\n<b>📧 Email:</b> {searched_user.email}"

        user_info += (
            f"\n\n🛡️ <b>Уровень доступа:</b> {get_role(searched_user.role)['name']}"
        )

        return {
            "user_info": user_info,
            "searched_default_user": searched_user.role in [1, 3],
            "is_head": is_head,
            "is_duty": is_duty,
            "is_mip": is_mip,
            "is_root": is_root,
            "is_casino_allowed": searched_user.is_casino_allowed,
            "is_trainee": searched_user.is_trainee,
        }

    except Exception as e:
        return {
            "user_info": f"❌ Ошибка при получении информации: {str(e)}",
            "is_head": is_head,
            "is_duty": is_duty,
            "is_mip": is_mip,
            "is_root": is_root,
        }


async def search_access_level_getter(
    user: Employee,
    stp_repo: MainRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict[str, str]:
    """Геттер получения доступных ролей для назначения сотруднику.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь со статусом ищущего сотрудника и доступных ролей для назначения
    """
    selected_user_id = dialog_manager.dialog_data.get("selected_user_id")
    selected_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))

    is_head = user.role == 2
    is_mip = user.role == 6
    is_root = user.role == 10

    # Форматируем роли для Radio виджета
    if is_head:
        formatted_roles = [
            (role_id, f"{role_data['emoji']} {role_data['name']}")
            for role_id, role_data in roles.items()
            if role_id in [1, 3]
        ]
    elif is_mip:
        formatted_roles = [
            (role_id, f"{role_data['emoji']} {role_data['name']}")
            for role_id, role_data in roles.items()
            if role_id not in [0, 10]
        ]
    elif is_root:
        formatted_roles = [
            (role_id, f"{role_data['emoji']} {role_data['name']}")
            for role_id, role_data in roles.items()
            if role_id != 0
        ]

    # Получаем информацию о выбранном пользователе
    selected_user_name = "Пользователь"
    current_role_name = ""
    current_role_id = None

    if selected_user_id:
        try:
            if selected_user:
                selected_user_name = format_fullname(
                    selected_user.fullname,
                    short=False,
                    gender_emoji=True,
                    username=selected_user.username,
                    user_id=selected_user.user_id,
                )
                role_info = get_role(selected_user.role)
                if role_info:
                    current_role_name = f"{role_info['emoji']} {role_info['name']}"
                current_role_id = selected_user.role

                # Устанавливаем текущую роль как выбранную в Radio
                access_level_radio = dialog_manager.find("access_level_select")
                if access_level_radio:
                    await access_level_radio.set_checked(str(current_role_id))
        except Exception:
            pass

    return {
        "roles": formatted_roles,
        "selected_user_name": selected_user_name,
        "current_role_name": current_role_name,
        "current_role_id": current_role_id,
    }


async def search_schedule_getter(
    stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> dict:
    """Геттер для получения графика выбранного пользователя.

    Args:
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с данными для отображения графика
    """
    selected_user_id = dialog_manager.dialog_data.get("selected_user_id")
    selected_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))

    schedule_data = await user_schedule_getter(
        user=selected_user, stp_repo=stp_repo, dialog_manager=dialog_manager
    )

    # Добавляем информацию о пользователе в начало текста графика
    user_name = format_fullname(
        selected_user.fullname,
        short=False,
        gender_emoji=True,
        username=selected_user.username,
        user_id=selected_user.user_id,
    )

    if "schedule_text" in schedule_data:
        schedule_data["schedule_text"] = (
            f"<b>{user_name}</b>\n\n<blockquote>{schedule_data['schedule_text']}</blockquote>"
        )

    return schedule_data


async def search_kpi_getter(
    stp_repo: MainRequestsRepo,
    kpi_repo: KPIRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict:
    """Геттер для получения KPI выбранного пользователя.

    Args:
        stp_repo: Репозиторий операций с базой STP
        kpi_repo: Репозиторий операций с базой KPI
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с данными KPI
    """
    selected_user_id = dialog_manager.dialog_data.get("selected_user_id")
    selected_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))

    # Вызываем оригинальный геттер с выбранным пользователем
    kpi_data = await kpi_getter(user=selected_user, kpi_repo=kpi_repo)

    # Добавляем информацию о пользователе в начало текста
    user_name = format_fullname(
        selected_user.fullname,
        short=False,
        gender_emoji=True,
        username=selected_user.username,
        user_id=selected_user.user_id,
    )

    if "kpi_text" in kpi_data:
        kpi_data["kpi_text"] = (
            f"<b>{user_name}</b>\n\n<blockquote>{kpi_data['kpi_text']}</blockquote>"
        )

    return kpi_data


async def search_kpi_requirements_getter(
    stp_repo: MainRequestsRepo,
    kpi_repo: KPIRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict:
    """Геттер для получения нормативов KPI выбранного пользователя.

    Args:
        stp_repo: Репозиторий операций с базой STP
        kpi_repo: Репозиторий операций с базой KPI
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с данными нормативов
    """
    selected_user_id = dialog_manager.dialog_data.get("selected_user_id")
    selected_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))

    # Вызываем оригинальный геттер с выбранным пользователем
    requirements_data = await kpi_requirements_getter(
        user=selected_user, kpi_repo=kpi_repo
    )

    # Добавляем информацию о пользователе в начало текста
    user_name = format_fullname(
        selected_user.fullname,
        short=False,
        gender_emoji=True,
        username=selected_user.username,
        user_id=selected_user.user_id,
    )

    if "requirements_text" in requirements_data:
        requirements_data["requirements_text"] = (
            f"<b>{user_name}</b>\n\n<blockquote>{requirements_data['requirements_text']}</blockquote>"
        )

    return requirements_data


async def search_salary_getter(
    stp_repo: MainRequestsRepo,
    kpi_repo: KPIRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict:
    """Геттер для получения зарплаты выбранного пользователя.

    Args:
        stp_repo: Репозиторий операций с базой STP
        kpi_repo: Репозиторий операций с базой KPI
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с данными зарплаты
    """
    selected_user_id = dialog_manager.dialog_data.get("selected_user_id")
    selected_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))

    # Вызываем оригинальный геттер с выбранным пользователем
    salary_data = await salary_getter(user=selected_user, kpi_repo=kpi_repo)

    # Добавляем информацию о пользователе в начало текста
    user_name = format_fullname(
        selected_user.fullname,
        short=False,
        gender_emoji=True,
        username=selected_user.username,
        user_id=selected_user.user_id,
    )

    if "salary_text" in salary_data:
        salary_data["salary_text"] = (
            f"<b>{user_name}</b>\n\n<blockquote>{salary_data['salary_text']}</blockquote>"
        )

    return salary_data


async def search_achievements_getter(
    stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> dict[str, Any]:
    """Геттер для получения достижений выбранного пользователя.

    Args:
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с историей достижений пользователя
    """
    selected_user_id = dialog_manager.dialog_data.get("selected_user_id")
    selected_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))

    # Получаем все транзакции-достижения пользователя
    transactions = await stp_repo.transaction.get_user_transactions(
        user_id=selected_user.user_id, only_achievements=True
    )

    # Получаем фильтр периода
    selected_period = dialog_manager.find(
        "search_achievement_period_filter"
    ).get_checked()

    # Фильтруем по периоду если нужно
    if selected_period != "all":
        # Получаем все достижения, чтобы найти период
        all_achievements = await stp_repo.achievement.get_achievements()
        achievement_periods = {ach.id: ach.period for ach in all_achievements}

        transactions = [
            t
            for t in transactions
            if t.source_id and achievement_periods.get(t.source_id) == selected_period
        ]

    # Форматируем достижения для отображения
    formatted_achievements = []
    for transaction in transactions:
        if not transaction.source_id:
            continue

        achievement = await stp_repo.achievement.get_achievements(
            achievement_id=transaction.source_id
        )
        if not achievement:
            continue

        period = "Неизвестно"
        match achievement.period:
            case "d":
                period = "Раз в день"
            case "w":
                period = "Раз в неделю"
            case "m":
                period = "Раз в месяц"
            case "A":
                period = "Вручную"

        date_str = transaction.created_at.strftime("%d.%m.%y %H:%M")

        formatted_achievements.append((
            transaction.id,
            escape(achievement.name),
            transaction.amount,
            escape(achievement.description),
            achievement.position,
            period,
            date_str,
        ))

    # Данные для радио-кнопок периодов
    period_radio_data = [
        ("all", "Все"),
        ("d", "День"),
        ("w", "Неделя"),
        ("m", "Месяц"),
        ("A", "Ручные"),
    ]

    user_name = format_fullname(
        selected_user.fullname,
        short=False,
        gender_emoji=True,
        username=selected_user.username,
        user_id=selected_user.user_id,
    )

    return {
        "achievements": formatted_achievements,
        "user_name": user_name,
        "total_achievements": len(formatted_achievements),
        "period_radio_data": period_radio_data,
        "selected_period": selected_period,
    }


async def search_inventory_getter(
    stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> dict[str, Any]:
    """Геттер для получения инвентаря выбранного пользователя.

    Args:
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с предметами инвентаря пользователя
    """
    selected_user_id = dialog_manager.dialog_data.get("selected_user_id")
    selected_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))

    # Получаем все покупки пользователя
    user_products = await stp_repo.purchase.get_user_purchases_with_details(
        user_id=selected_user.user_id
    )

    total_bought = len(user_products)

    # Получаем фильтр статуса
    filter_type = dialog_manager.find("search_inventory_filter").get_checked()

    formatted_products = []
    for product in user_products:
        user_product = product.user_purchase
        product_info = product.product_info

        # Применяем фильтр
        if filter_type != "all" and user_product.status != filter_type:
            continue

        date_str = user_product.bought_at.strftime("%d.%m.%y")
        status_emoji = get_status_emoji(user_product.status)
        usage_info = f"({product.current_usages}/{product.max_usages})"
        button_text = f"{status_emoji} {usage_info} {product_info.name} ({date_str})"

        formatted_products.append((
            user_product.id,
            button_text,
            product_info.name,
            product_info.description,
            product_info.cost,
            user_product.status,
            product.current_usages,
            product.max_usages,
        ))

    user_name = format_fullname(
        selected_user.fullname,
        short=False,
        gender_emoji=True,
        username=selected_user.username,
        user_id=selected_user.user_id,
    )

    return {
        "products": formatted_products,
        "user_name": user_name,
        "total_bought": total_bought,
        "total_shown": len(formatted_products),
        "inventory_filter": filter_type,
    }

"""Геттеры для функций управления составом группы."""

from typing import Any

from aiogram_dialog import DialogManager
from stp_database import Employee, MainRequestsRepo
from stp_database.repo.KPI.requests import KPIRequestsRepo

from tgbot.dialogs.getters.common.game.kpi import (
    base_kpi_data,
    kpi_getter,
    kpi_requirements_getter,
    salary_getter,
)
from tgbot.dialogs.getters.common.schedules import user_schedule_getter
from tgbot.misc.dicts import roles
from tgbot.misc.helpers import format_fullname, get_role
from tgbot.services.search import SearchService


async def group_members_getter(
    user: Employee, stp_repo: MainRequestsRepo, **_kwargs
) -> dict[str, Any]:
    """Геттер для получения списка членов группы руководителя.

    Args:
        user: Экземпляр пользователя с моделью Employee (руководитель)
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь со списком членов группы
    """
    # Получаем всех пользователей с данным руководителем
    group_members = await stp_repo.employee.get_users(head=user.fullname)

    # Сортируем по ФИО
    sorted_members = sorted(group_members, key=lambda k: k.fullname)

    # Форматируем для отображения
    formatted_members = []
    for member in sorted_members:
        role_info = get_role(member.role)
        formatted_members.append((
            member.id,
            format_fullname(member.fullname, True, True),
            role_info["emoji"] if role_info else "",
        ))

    return {
        "members_list": formatted_members,
        "total_members": len(formatted_members),
    }


async def member_info_getter(
    stp_repo: MainRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict[str, str]:
    """Геттер для получения информации о выбранном члене группы.

    Args:
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с информацией о выбранном сотруднике
    """
    selected_user_id = dialog_manager.dialog_data.get("selected_member_id")

    if not selected_user_id:
        return {"user_info": "❌ Пользователь не выбран"}

    try:
        # Получаем информацию о пользователе
        searched_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))
        if not searched_user:
            return {"user_info": "❌ Пользователь не найден"}

        # Получаем руководителя если есть
        searched_user_head = None
        if searched_user.head:
            searched_user_head = await stp_repo.employee.get_users(
                fullname=searched_user.head
            )

        # Формируем информацию о пользователе
        user_info = SearchService.format_user_info_base(
            searched_user, searched_user_head
        )

        return {
            "user_info": user_info,
            "is_casino_allowed": searched_user.is_casino_allowed,
        }

    except Exception as e:
        return {"user_info": f"❌ Ошибка при получении информации: {str(e)}"}


async def member_access_level_getter(
    stp_repo: MainRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict[str, str]:
    """Геттер получения доступных ролей для назначения члену группы.

    Args:
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь со статусом руководителя и доступных ролей для назначения
    """
    selected_user_id = dialog_manager.dialog_data.get("selected_member_id")
    selected_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))

    # Форматируем роли для Select виджета (только специалисты и стажеры для руководителей)
    formatted_roles = [
        (role_id, f"{role_data['emoji']} {role_data['name']}")
        for role_id, role_data in roles.items()
        if role_id in [1, 3]
    ]

    # Получаем информацию о выбранном пользователе
    selected_user_name = "Пользователь"
    current_role_name = ""

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
        except Exception:
            pass

    return {
        "roles": formatted_roles,
        "selected_user_name": selected_user_name,
        "current_role_name": current_role_name,
    }


async def member_schedule_getter(
    stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> dict:
    """Геттер для получения графика выбранного члена группы.

    Args:
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с данными для отображения графика
    """
    selected_user_id = dialog_manager.dialog_data.get("selected_member_id")
    selected_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))

    schedule_data = await user_schedule_getter(
        user=selected_user, stp_repo=stp_repo, dialog_manager=dialog_manager
    )

    # Добавляем информацию о пользователе в начало текста графика
    user_name = format_fullname(
        selected_user.fullname,
        short=False,
        gender_emoji=True,
    )

    if "schedule_text" in schedule_data:
        schedule_data["schedule_text"] = (
            f"<b>{user_name}</b>\n\n<blockquote>{schedule_data['schedule_text']}</blockquote>"
        )

    return schedule_data


async def member_kpi_getter(
    stp_repo: MainRequestsRepo,
    kpi_repo: KPIRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict:
    """Геттер для получения KPI выбранного члена группы.

    Args:
        stp_repo: Репозиторий операций с базой STP
        kpi_repo: Репозиторий операций с базой KPI
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с данными KPI
    """
    selected_user_id = dialog_manager.dialog_data.get("selected_member_id")
    selected_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))

    # Получаем данные премии
    premium_data = await base_kpi_data(user=selected_user, kpi_repo=kpi_repo)
    premium = premium_data.get("premium")

    # Вызываем оригинальный геттер с выбранным пользователем
    kpi_data = await kpi_getter(user=selected_user, premium=premium)

    # Добавляем информацию о пользователе в начало текста
    user_name = format_fullname(
        selected_user.fullname,
        short=False,
        gender_emoji=True,
    )

    if "kpi_text" in kpi_data:
        kpi_data["kpi_text"] = (
            f"<b>{user_name}</b>\n\n<blockquote>{kpi_data['kpi_text']}</blockquote>"
        )

    return kpi_data


async def member_kpi_requirements_getter(
    stp_repo: MainRequestsRepo,
    kpi_repo: KPIRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict:
    """Геттер для получения нормативов KPI выбранного члена группы.

    Args:
        stp_repo: Репозиторий операций с базой STP
        kpi_repo: Репозиторий операций с базой KPI
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с данными нормативов
    """
    selected_user_id = dialog_manager.dialog_data.get("selected_member_id")
    selected_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))

    # Получаем данные премии
    premium_data = await base_kpi_data(user=selected_user, kpi_repo=kpi_repo)
    premium = premium_data.get("premium")

    # Вызываем оригинальный геттер с выбранным пользователем
    requirements_data = await kpi_requirements_getter(
        user=selected_user, premium=premium
    )

    # Добавляем информацию о пользователе в начало текста
    user_name = format_fullname(
        selected_user.fullname,
        short=False,
        gender_emoji=True,
    )

    if "requirements_text" in requirements_data:
        requirements_data["requirements_text"] = (
            f"<b>{user_name}</b>\n\n<blockquote>{requirements_data['requirements_text']}</blockquote>"
        )

    return requirements_data


async def member_salary_getter(
    stp_repo: MainRequestsRepo,
    kpi_repo: KPIRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> dict:
    """Геттер для получения зарплаты выбранного члена группы.

    Args:
        stp_repo: Репозиторий операций с базой STP
        kpi_repo: Репозиторий операций с базой KPI
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с данными зарплаты
    """
    selected_user_id = dialog_manager.dialog_data.get("selected_member_id")
    selected_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))

    # Получаем данные премии
    premium_data = await base_kpi_data(user=selected_user, kpi_repo=kpi_repo)
    premium = premium_data.get("premium")

    # Вызываем оригинальный геттер с выбранным пользователем
    salary_data = await salary_getter(user=selected_user, premium=premium)

    # Добавляем информацию о пользователе в начало текста
    user_name = format_fullname(
        selected_user.fullname,
        short=False,
        gender_emoji=True,
    )

    if "salary_text" in salary_data:
        salary_data["salary_text"] = (
            f"<b>{user_name}</b>\n\n<blockquote>{salary_data['salary_text']}</blockquote>"
        )

    return salary_data


async def member_achievements_getter(
    stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> dict[str, Any]:
    """Геттер для получения достижений выбранного члена группы.

    Args:
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с историей достижений пользователя
    """
    from html import escape

    selected_user_id = dialog_manager.dialog_data.get("selected_member_id")
    selected_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))

    # Получаем все транзакции-достижения пользователя
    transactions = await stp_repo.transaction.get_user_transactions(
        user_id=selected_user.user_id, only_achievements=True
    )

    # Получаем фильтр периода
    selected_period = dialog_manager.find(
        "member_achievement_period_filter"
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

    user_name = format_fullname(selected_user.fullname, short=False, gender_emoji=True)

    return {
        "achievements": formatted_achievements,
        "user_name": user_name,
        "total_achievements": len(formatted_achievements),
        "period_radio_data": period_radio_data,
        "selected_period": selected_period,
    }


async def member_inventory_getter(
    stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> dict[str, Any]:
    """Геттер для получения инвентаря выбранного члена группы.

    Args:
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с предметами инвентаря пользователя
    """
    from tgbot.misc.helpers import get_status_emoji

    selected_user_id = dialog_manager.dialog_data.get("selected_member_id")
    selected_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))

    # Получаем все покупки пользователя
    user_products = await stp_repo.purchase.get_user_purchases_with_details(
        user_id=selected_user.user_id
    )

    total_bought = len(user_products)

    # Получаем фильтр статуса
    filter_type = dialog_manager.find("member_inventory_filter").get_checked()

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

    user_name = format_fullname(selected_user.fullname, short=False, gender_emoji=True)

    return {
        "products": formatted_products,
        "user_name": user_name,
        "total_bought": total_bought,
        "total_shown": len(formatted_products),
        "inventory_filter": filter_type,
    }

from aiogram_dialog import DialogManager

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.misc.helpers import get_role
from tgbot.services.search import SearchService


def short_name(full_name: str) -> str:
    """Extract short name from full name."""
    clean_name = full_name.split("(")[0].strip()
    parts = clean_name.split()

    if len(parts) >= 2:
        return " ".join(parts[:2])
    return clean_name


async def main_search_getter(stp_repo: MainRequestsRepo, **kwargs):
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


async def search_specialists_getter(dialog_manager: DialogManager, **kwargs):
    base_data = await main_search_getter(**kwargs)
    specialists = base_data.get("specialists")

    selected_division = dialog_manager.dialog_data.get("search_divisions", "all")

    # Устанавливаем стандартное значение если не указано иное
    if "search_divisions" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["search_divisions"] = "all"

    # Фильтруем руководителей по направлению если выбран фильтр
    if selected_division != "all":
        specialists = [s for s in specialists if s.division == selected_division]

    sorted_specialists = sorted(specialists, key=lambda k: k.fullname)

    formatted_specialists = []
    for specialist in sorted_specialists:
        role_info = get_role(specialist.role)
        formatted_specialists.append(
            (specialist.id, short_name(specialist.fullname), role_info["emoji"])
        )

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


async def search_heads_getter(dialog_manager: DialogManager, **kwargs):
    base_data = await main_search_getter(**kwargs)
    all_heads = base_data.get("heads")

    selected_division = dialog_manager.dialog_data.get("search_divisions", "all")

    # Устанавливаем стандартное значение если не указано иное
    if "search_divisions" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["search_divisions"] = "all"

    # Фильтруем руководителей по направлению если выбран фильтр
    if selected_division != "all":
        all_heads = [s for s in all_heads if s.division == selected_division]

    sorted_heads = sorted(all_heads, key=lambda k: k.fullname)

    formatted_heads = []
    for head in sorted_heads:
        role_info = get_role(head.role)
        formatted_heads.append((head.id, short_name(head.fullname), role_info["emoji"]))

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


async def search_results_getter(dialog_manager: DialogManager, **kwargs):
    """Получение результатов поиска"""
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
    **kwargs,
):
    """Получение информации о выбранном пользователе"""
    selected_user_id = dialog_manager.dialog_data.get("selected_user_id")

    if not selected_user_id:
        return {"user_info": "❌ Пользователь не выбран"}

    try:
        # Получаем информацию о пользователе
        searched_user = await stp_repo.employee.get_user(main_id=int(selected_user_id))
        if not searched_user:
            searched_user = await stp_repo.employee.get_user(
                user_id=int(selected_user_id)
            )
        if not searched_user:
            return {"user_info": "❌ Пользователь не найден"}

        # Получаем руководителя если есть
        searched_user_head = None
        if searched_user.head:
            searched_user_head = await stp_repo.employee.get_user(
                fullname=searched_user.head
            )

        # Получаем роль текущего пользователя из базовых данных
        viewer_role = user.role if user else 1

        # Формируем информацию о пользователе с учетом роли просматривающего
        user_info = SearchService.format_user_info_role_based(
            searched_user, searched_user_head, viewer_role
        )

        # Добавляем статистику для руководителей если просматривает пользователь с ролью 2
        if searched_user.role == 2 and viewer_role >= 2:
            group_stats = await SearchService.get_group_statistics_by_id(
                searched_user.user_id, stp_repo
            )
            if group_stats["total_users"] > 0:
                user_info += SearchService.format_head_group_info(group_stats)

        return {"user_info": user_info}

    except Exception as e:
        return {
            "user_info": f"❌ Ошибка при получении информации: {str(e)}",
        }

"""Геттеры для меню списка достижений специалистов."""

from html import escape
from typing import Any, Dict

from stp_database import Employee, MainRequestsRepo


async def achievements_getter(stp_repo: MainRequestsRepo, **_kwargs) -> Dict[str, Any]:
    """Геттер получения списка достижений.

    Returns:
        Словарь отформатированных к отображению достижений
    """
    if "division" in _kwargs:
        achievements_list = await stp_repo.achievement.get_achievements(
            division=_kwargs["division"]
        )
    else:
        achievements_list = await stp_repo.achievement.get_achievements()

    formatted_achievements = []
    for achievement in achievements_list:
        period = "Неизвестно"  # Стандартное значение
        match achievement.period:
            case "d":
                period = "Раз в день"
            case "w":
                period = "Раз в неделю"
            case "m":
                period = "Раз в месяц"
            case "A":
                period = "Вручную"
            case _:
                period = "Неизвестно"

        formatted_achievements.append((
            achievement.id,
            escape(achievement.name),
            achievement.reward,
            escape(achievement.description),
            achievement.position,
            period,
            achievement.division,
        ))

    return {
        "achievements": formatted_achievements,
    }


async def user_achievements_getter(
    user: Employee, stp_repo: MainRequestsRepo, **kwargs
) -> Dict[str, Any]:
    """Получение достижений для конкретного подразделения пользователя.

    Args:
        stp_repo: Репозиторий операций с базой STP
        user: Экземпляр пользователя с моделью Employee

    Returns:
        Возвращает словарь доступных достижений для направления сотрудника
    """
    # Передаем направление пользователя в базовый getter
    return await achievements_getter(
        stp_repo=stp_repo, division="НЦК" if "НЦК" in user.division else "НТП", **kwargs
    )

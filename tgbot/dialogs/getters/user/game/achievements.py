from html import escape

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo


async def achievements_getter(**kwargs):
    stp_repo: MainRequestsRepo = kwargs.get("stp_repo")

    if "division" in kwargs:
        achievements_list = await stp_repo.achievement.get_achievements(
            division=kwargs["division"]
        )
    else:
        achievements_list = await stp_repo.achievement.get_achievements()

    formatted_achievements = []
    for achievement in achievements_list:
        period = "Неизвестно"  # Default value
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

        formatted_achievements.append(
            (
                achievement.id,
                escape(achievement.name),
                achievement.reward,
                escape(achievement.description),
                achievement.position,
                period,
                achievement.division,
            )
        )

    return {
        "achievements": formatted_achievements,
    }


async def user_achievements_getter(**kwargs):
    """
    Получение достижений для конкретного подразделения пользователя
    """
    user: Employee = kwargs.get("user")

    # Передаем division пользователя в базовый getter
    return await achievements_getter(
        division="НЦК" if "НЦК" in user.division else "НТП", **kwargs
    )

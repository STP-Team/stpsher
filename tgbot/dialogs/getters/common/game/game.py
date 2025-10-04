"""Геттеры для игрового профиля."""

from typing import Dict

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.services.leveling import LevelingSystem


async def game_getter(
    user: Employee, stp_repo: MainRequestsRepo, **_kwargs
) -> Dict[str, str]:
    """Геттер получения информации об игровой профиле сотрудника.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь с данными об игровом профиле сотрудника
    """
    user_balance = await stp_repo.transaction.get_user_balance(user_id=user.user_id)
    achievements_sum = await stp_repo.transaction.get_user_achievements_sum(
        user_id=user.user_id
    )
    purchases_sum = await stp_repo.purchase.get_user_purchases_sum(user_id=user.user_id)
    level_info = LevelingSystem.get_level_info_text(achievements_sum, user_balance)

    return {
        "achievements_sum": achievements_sum,
        "purchases_sum": purchases_sum,
        "level_info": level_info,
        "is_user": user.role in [1, 3],
        "activations_access": user.role in [2, 3, 5, 6],
    }

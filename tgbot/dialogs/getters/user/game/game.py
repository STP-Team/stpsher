from typing import Any, Dict

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.services.leveling import LevelingSystem


async def game_getter(
    user: Employee, stp_repo: MainRequestsRepo, **kwargs
) -> Dict[str, Any]:
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
        "is_duty": user.role == 3,
    }

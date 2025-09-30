from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.dialogs.getters.common.db_getters import db_getter
from tgbot.services.leveling import LevelingSystem


async def game_getter(**kwargs):
    base_data = await db_getter(**kwargs)
    stp_repo: MainRequestsRepo = base_data.get("stp_repo")
    user: Employee = base_data.get("user")

    user_balance = await stp_repo.transaction.get_user_balance(user_id=user.user_id)
    achievements_sum = await stp_repo.transaction.get_user_achievements_sum(
        user_id=user.user_id
    )
    purchases_sum = await stp_repo.purchase.get_user_purchases_sum(user_id=user.user_id)
    level_info = LevelingSystem.get_level_info_text(achievements_sum, user_balance)

    return {
        **base_data,
        "achievements_sum": achievements_sum,
        "purchases_sum": purchases_sum,
        "level_info": level_info,
        "is_duty": user.role == 3,
    }


async def activation_detail_getter(**kwargs):
    """
    Getter for activation detail window that includes dialog_data
    """
    base_data = await db_getter(**kwargs)
    dialog_manager = kwargs.get("dialog_manager")

    # Получаем selected_activation из dialog_data
    selected_activation = dialog_manager.dialog_data.get("selected_activation", {})

    # Подготавливаем данные с вычисленными значениями
    if selected_activation:
        # Вычисляем следующий номер активации
        next_usage_count = selected_activation.get("usage_count", 0) + 1
        selected_activation = {
            **selected_activation,
            "next_usage_count": next_usage_count,
        }

    return {
        **base_data,
        "selected_activation": selected_activation,
    }

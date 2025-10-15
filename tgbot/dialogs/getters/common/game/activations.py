"""Геттеры для окон активации предметов."""

from typing import Dict

from aiogram_dialog import DialogManager
from stp_database import Employee, MainRequestsRepo

from tgbot.misc.helpers import format_fullname


async def activations_getter(
    stp_repo: MainRequestsRepo, user: Employee, **_kwargs
) -> Dict:
    """Получение списка предметов для активации на основе роли пользователя.

    Args:
        stp_repo: Репозиторий операций с базой STP
        user: Экземпляр пользователя с моделью Employee

    Returns:
        Словарь из предметов на активацию
    """
    # Получаем покупки, ожидающие активации с manager_role, соответствующей роли пользователя
    if user.role in [2, 3]:
        activations = await stp_repo.purchase.get_review_purchases_for_activation(
            manager_role=3,
            division="НЦК" if user.division == "НЦК" else ["НТП", "НТП1"],
        )
    else:
        activations = await stp_repo.purchase.get_review_purchases_for_activation(
            manager_role=user.role, division=None
        )

    formatted_activations = []
    for counter, purchase_details in enumerate(activations, start=1):
        purchase = purchase_details.user_purchase
        product = purchase_details.product_info

        # Получаем информацию о пользователе, который купил предмет
        purchase_user = await stp_repo.employee.get_users(user_id=purchase.user_id)
        purchase_user_text = format_fullname(
            purchase_user.fullname,
            True,
            True,
            purchase_user.username,
            purchase_user.user_id,
        )

        formatted_activations.append((
            purchase.id,  # ID для обработчика клика
            product.name,
            product.description,
            purchase.bought_at.strftime("%d.%m.%Y в %H:%M"),
            purchase_user_text,
            purchase_user.division if purchase_user else "Неизвестно",
            purchase_user.username if purchase_user else None,
            purchase_user.user_id if purchase_user else purchase.user_id,
        ))

    return {
        "activations": formatted_activations,
        "total_activations": len(formatted_activations),
    }


async def activation_detail_getter(dialog_manager: DialogManager, **_kwargs):
    """Геттер для расчета кол-ва использований предмета.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь информации об активации предмета с кол-вом оставшихся использований предмета
    """
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

    # Формируем текст комментария пользователя
    user_comment_text = ""
    if selected_activation.get("user_comment"):
        user_comment_text = f"""

💬 <b>Комментарий специалиста:</b>
<blockquote>{selected_activation["user_comment"]}</blockquote>"""

    return {
        "selected_activation": selected_activation,
        "user_comment_text": user_comment_text,
    }

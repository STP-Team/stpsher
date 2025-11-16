"""Геттеры для окон активации предметов."""

from typing import Dict

from aiogram_dialog import DialogManager
from stp_database import Employee, MainRequestsRepo

from tgbot.misc.helpers import format_fullname, strftime_date


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
            division="НЦК" if user.division == "НЦК" else ["НТП1", "НТП2"],
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
            purchase_user,
            True,
            True,
        )

        formatted_activations.append((
            purchase.id,  # ID для обработчика клика
            product.name,
            product.description,
            purchase.bought_at.strftime(strftime_date),
            purchase_user_text,
            purchase_user.division if purchase_user else "Неизвестно",
            purchase_user.username if purchase_user else None,
            purchase_user.user_id if purchase_user else purchase.user_id,
        ))

    return {
        "activations": formatted_activations,
        "total_activations": len(formatted_activations),
    }


async def activation_detail_getter(
    dialog_manager: DialogManager, stp_repo: MainRequestsRepo, **_kwargs
):
    """Геттер для расчета кол-ва использований предмета.

    Args:
        dialog_manager: Менеджер диалога
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь информации об активации предмета с кол-вом оставшихся использований предмета
    """
    purchase_id = dialog_manager.dialog_data.setdefault(
        "purchase_id",
        dialog_manager.start_data.get("purchase_id")
        if dialog_manager.start_data
        else None,
    )

    if not purchase_id:
        return {
            "selected_activation": {},
            "user_comment_text": "",
        }

    # Получаем детали покупки из базы данных
    purchase_details = await stp_repo.purchase.get_purchase_details(purchase_id)

    if not purchase_details:
        return {
            "selected_activation": {},
            "user_comment_text": "",
        }

    purchase = purchase_details.user_purchase
    product = purchase_details.product_info

    # Получаем информацию о пользователе, который купил предмет
    purchase_user = await stp_repo.employee.get_users(user_id=purchase.user_id)
    purchase_user_text = format_fullname(
        purchase_user,
        True,
        True,
    )

    # Вычисляем следующий номер активации
    next_usage_count = purchase.usage_count + 1

    # Формируем данные активации
    selected_activation = {
        "id": purchase.id,
        "product_name": product.name,
        "product_description": product.description,
        "product_cost": product.cost,
        "product_count": product.count,
        "bought_at": purchase.bought_at.strftime(strftime_date),
        "user_name": purchase_user_text,
        "user_position": purchase_user.position if purchase_user else "Неизвестно",
        "user_division": purchase_user.division if purchase_user else "Неизвестно",
        "user_head": purchase_user.head if purchase_user else "Неизвестно",
        "fullname": purchase_user_text,
        "username": purchase_user.username if purchase_user else None,
        "user_id": purchase_user.user_id if purchase_user else purchase.user_id,
        "usage_count": purchase.usage_count,
        "user_comment": purchase.user_comment,
        "next_usage_count": next_usage_count,
    }

    # Формируем текст комментария пользователя
    user_comment_text = ""
    if purchase.user_comment:
        user_comment_text = f"""

💬 <b>Комментарий специалиста:</b>
<blockquote>{purchase.user_comment}</blockquote>"""

    return {
        "selected_activation": selected_activation,
        "user_comment_text": user_comment_text,
    }

"""Геттеры для меню магазина специалистов."""

from typing import Any, Dict

from aiogram_dialog import DialogManager

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo


async def products_getter(
    user: Employee, stp_repo: MainRequestsRepo, division: str = None, **_kwargs
) -> Dict[str, Any]:
    """Геттер для получения списка предметов магазина.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        division: Фильтр по подразделению (опционально)

    Returns:
        Словарь из списка предметов и баланса сотрудника
    """
    user_balance: int = await stp_repo.transaction.get_user_balance(
        user_id=user.user_id
    )

    # Для менеджеров загружаем все продукты или фильтруем по указанному подразделению
    # Для обычных пользователей - только их подразделение
    if division is not None:
        products = await stp_repo.product.get_products(division=division)
    else:
        products = await stp_repo.product.get_products(division=user.division)

    formatted_products = []
    for product in products:
        formatted_products.append(
            (
                product.id,
                product.name,
                product.description,
                product.count,
                product.cost,
                product.division,
            )
        )

    return {
        "products": formatted_products,
        "user_balance": user_balance,
    }


async def confirmation_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна подтверждения покупки предмета.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с информацией о выбранном предмете для покупки
    """
    product_info = dialog_manager.dialog_data.get("selected_product")
    user_balance = dialog_manager.dialog_data.get("user_balance", 0)

    if not product_info:
        return {}

    balance_after_purchase = user_balance - product_info["cost"]

    return {
        "product_name": product_info["name"],
        "product_description": product_info["description"],
        "product_count": product_info["count"],
        "product_cost": product_info["cost"],
        "user_balance": user_balance,
        "balance_after_purchase": balance_after_purchase,
    }


async def success_getter(dialog_manager: DialogManager, **_kwargs) -> Dict[str, Any]:
    """Геттер для окна успешной покупки предмета.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с информацией о приобретенном предмете и изменении баланса
    """
    product_info = dialog_manager.dialog_data.get("selected_product")
    user_balance = dialog_manager.dialog_data.get("user_balance", 0)
    new_balance = dialog_manager.dialog_data.get("new_balance", 0)

    if not product_info:
        return {}

    return {
        "product_name": product_info["name"],
        "product_description": product_info["description"],
        "product_count": product_info["count"],
        "product_cost": product_info["cost"],
        "user_balance": user_balance,
        "new_balance": new_balance,
    }

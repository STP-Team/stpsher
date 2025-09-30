from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo


async def products_getter(**kwargs):
    """
    Получение списка предметов для магазина
    """
    stp_repo: MainRequestsRepo = kwargs.get("stp_repo")
    user: Employee = kwargs.get("user")

    user_balance: int = await stp_repo.transaction.get_user_balance(
        user_id=user.user_id
    )
    products = await stp_repo.product.get_products(division=user.division)

    formatted_products = []
    for product in products:
        formatted_products.append(
            (product.id, product.name, product.description, product.count, product.cost)
        )

    return {
        "products": formatted_products,
        "user_balance": user_balance,
    }


async def confirmation_getter(**kwargs):
    """
    Геттер для окна подтверждения покупки
    """
    dialog_manager = kwargs.get("dialog_manager")
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


async def success_getter(**kwargs):
    """
    Геттер для окна успешной покупки
    """
    dialog_manager = kwargs.get("dialog_manager")
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

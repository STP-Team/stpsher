from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo


async def role_based_products_getter(**kwargs):
    """
    Получение списка предметов для магазина с учетом роли пользователя
    """
    stp_repo: MainRequestsRepo = kwargs.get("stp_repo")
    user: Employee = kwargs.get("user")

    user_balance: int = await stp_repo.transaction.get_user_balance(
        user_id=user.user_id
    )

    # Определяем какие продукты показывать в зависимости от роли
    if user.role == 6:  # GOK role
        # Для GOK показываем все продукты из всех подразделений
        products = await stp_repo.product.get_products()
    else:
        # Для специалистов показываем продукты своего подразделения
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


async def role_based_product_filter_getter(**kwargs):
    """
    Фильтрует предметы в зависимости от выбранного радио-фильтра с учетом роли
    """
    base_data = await role_based_products_getter(**kwargs)
    dialog_manager = kwargs.get("dialog_manager")

    # Проверяем текущий выбор фильтра
    filter_type = dialog_manager.dialog_data.get("product_filter", "available")

    # Устанавливаем стандартный фильтр если не установлено иное
    if "product_filter" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["product_filter"] = "available"

    products = base_data["products"]
    user_balance = base_data["user_balance"]

    if filter_type == "available":
        # Фильтруем предметы, доступные пользователю
        filtered_products = [p for p in products if p[4] <= user_balance]
    else:  # "Все предметы"
        filtered_products = products

    return {
        "products": filtered_products,
        "user_balance": user_balance,
        "product_filter": filter_type,
    }

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo


async def product_getter(**kwargs):
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


def get_status_emoji(status: str) -> str:
    """Возвращает эмодзи в зависимости от статуса"""
    status_emojis = {
        "stored": "📦",
        "review": "⏳",
        "used_up": "🔒",
        "canceled": "🔥",
        "rejected": "⛔",
    }
    return status_emojis.get(status, "❓")


async def inventory_getter(**kwargs):
    stp_repo: MainRequestsRepo = kwargs.get("stp_repo")
    user: Employee = kwargs.get("user")

    user_products = await stp_repo.purchase.get_user_purchases_with_details(
        user_id=user.user_id
    )

    total_bought: int = len(user_products)

    formatted_products = []
    for product in user_products:
        user_product = product.user_purchase
        product_info = product.product_info

        date_str = user_product.bought_at.strftime("%d.%m.%y")
        status_emoji = get_status_emoji(user_product.status)
        usage_info = f"({product.current_usages}/{product.max_usages})"
        button_text = f"{status_emoji} {usage_info} {product_info.name} ({date_str})"

        formatted_products.append(
            (
                user_product.id,  # ID для обработчика клика
                button_text,  # Текст кнопки с эмодзи и статусом
                product_info.name,
                product_info.description,
                product_info.cost,
                user_product.status,
                product.current_usages,
                product.max_usages,
            )
        )

    return {
        "total_bought": total_bought,
        "products": formatted_products,
    }


async def inventory_filter_getter(**kwargs):
    """
    Фильтрует предметы в инвентаре в зависимости от выбранного радио-фильтра
    """
    base_data = await inventory_getter(**kwargs)
    dialog_manager = kwargs.get("dialog_manager")

    # Проверяем текущий выбор фильтра (стандартно на 'all')
    filter_type = dialog_manager.dialog_data.get("purchases_filter", "all")

    # Устанавливаем стандартный фильтр если не установлено иное
    if "purchases_filter" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["purchases_filter"] = "all"

    products = base_data["products"]
    total_bought = base_data["total_bought"]

    if filter_type != "all":
        # Фильтруем предметы по статусу
        filtered_products = [
            p
            for p in products
            if p[5] == filter_type  # p[5] это status
        ]
    else:
        filtered_products = products

    return {
        "products": filtered_products,
        "total_bought": total_bought,
        "inventory_filter": filter_type,
    }


async def inventory_detail_getter(**kwargs):
    """
    Геттер для окна детального просмотра предмета инвентаря
    """
    dialog_manager = kwargs.get("dialog_manager")
    product_info = dialog_manager.dialog_data.get("selected_inventory_product")

    if not product_info:
        return {}

    status_names = {
        "stored": "Готов к использованию",
        "review": "На проверке",
        "used_up": "Полностью использован",
        "canceled": "Отменен",
        "rejected": "Отклонен",
    }
    status_name = status_names.get(product_info["status"], "Неизвестный статус")

    # Проверяем возможные действия с купленным предметом
    can_use = (
        product_info["status"] == "stored"
        and product_info["current_usages"] < product_info["max_usages"]
    )

    # Можно продать только если статус "stored" И usage_count равен 0 (не использовался)
    can_sell = product_info["status"] == "stored" and product_info["usage_count"] == 0

    # Можно отменить активацию если статус "review" (на проверке)
    can_cancel = product_info["status"] == "review"

    # Формируем дополнительные тексты
    comment_text = ""
    if product_info.get("comment"):
        comment_text = f"\n\n<b>💬 Комментарий</b>\n└ {product_info['comment']}"

    updated_by_text = ""
    if product_info.get("updated_by_user_id") and product_info.get("updated_at"):
        updated_by_text = f"\n\n<blockquote expandable><b>👤 Последняя проверка</b>\n<b>📅 Дата проверки:</b> {product_info['updated_at']}</blockquote>"

    return {
        "product_name": product_info["product_name"],
        "product_description": product_info["product_description"],
        "product_cost": product_info["product_cost"],
        "product_count": product_info["product_count"],
        "status_name": status_name,
        "usage_count": product_info["usage_count"],
        "bought_at": product_info["bought_at"],
        "comment_text": comment_text,
        "updated_by_text": updated_by_text,
        "can_use": can_use,
        "can_sell": can_sell,
        "can_cancel": can_cancel,
    }


async def product_filter_getter(**kwargs):
    """
    Фильтрует предметы в зависимости от выбранного радио-фильтра
    """
    base_data = await product_getter(**kwargs)
    dialog_manager = kwargs.get("dialog_manager")

    # Проверяем текущий выбор фильтра (стандартно на 'Доступные')
    filter_type = dialog_manager.dialog_data.get("product_filter", "available")

    # Устанавливаем стандартный фильтр если не установлено иное
    if "product_filter" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["product_filter"] = "available"

    products = base_data["products"]
    user_balance = base_data["user_balance"]

    if filter_type == "available":
        # Фильтруем предметы, доступные пользователю
        filtered_products = [
            p for p in products if p[4] <= user_balance
        ]  # p[4] это стоимость
    else:  # "Все предметы"
        filtered_products = products

    return {
        "products": filtered_products,
        "user_balance": user_balance,
        "product_filter": filter_type,
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

"""Геттеры для инвентаря."""

from typing import Any, Dict

from aiogram_dialog import DialogManager
from stp_database import Employee, MainRequestsRepo

from tgbot.misc.helpers import get_status_emoji


async def inventory_getter(
    user: Employee, stp_repo: MainRequestsRepo, **_kwargs
) -> Dict[str, Any]:
    """Геттер получения предметов из инвентаря пользователя.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь со списком предметов в инвентаре пользователя
    """
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

        formatted_products.append((
            user_product.id,  # ID для обработчика клика
            button_text,  # Текст кнопки с эмодзи и статусом
            product_info.name,
            product_info.description,
            product_info.cost,
            user_product.status,
            product.current_usages,
            product.max_usages,
        ))

    return {
        "total_bought": total_bought,
        "products": formatted_products,
    }


async def inventory_detail_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна детального просмотра предмета инвентаря.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с информацией о выбранном предмете инвентаря
    """
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
        "came_from_products": dialog_manager.dialog_data.get(
            "came_from_products", False
        ),
    }

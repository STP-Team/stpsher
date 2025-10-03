"""Геттеры для меню предметов/магазина."""

from typing import Any

from aiogram_dialog import DialogManager

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo


async def role_based_products_getter(
    user: Employee, stp_repo: MainRequestsRepo, **_kwargs
) -> dict[str, list[Any] | int]:
    """Геттер для получения списка предметов магазина с учетом роли пользователя.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь предметов, отфильтрованных в зависимости от роли сотрудника
    """
    user_balance: int = await stp_repo.transaction.get_user_balance(
        user_id=user.user_id
    )

    # Определяем какие продукты показывать в зависимости от роли
    if user.role in [5, 6]:  # ГОК и МИП
        # Показываем все продукты из всех направлений
        products = await stp_repo.product.get_products()
    else:
        # Для специалистов показываем продукты своего направления
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


async def role_based_product_filter_getter(
    user: Employee, stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **kwargs
) -> dict[str, list[Any] | int | str | bool | list[tuple[str, str]]]:
    """Фильтрует предметы в зависимости от выбранного фильтра.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь отфильтрованных предметов
    """
    base_data = await role_based_products_getter(user=user, stp_repo=stp_repo, **kwargs)

    is_user = user.role in [1, 3]

    # Данные для радио-кнопок подразделений (для администраторов/ГОК/МИП)
    division_radio_data = [
        ("all", "Все"),
        ("nck", "НЦК"),
        ("ntp", "НТП"),
    ]

    products = base_data["products"]
    user_balance = base_data["user_balance"]

    # Для обычных пользователей (специалисты/дежурные)
    if is_user:
        # Проверяем текущий выбор фильтра
        filter_type = dialog_manager.dialog_data.get("product_filter", "available")

        # Устанавливаем стандартный фильтр если не установлено иное
        if "product_filter" not in dialog_manager.dialog_data:
            dialog_manager.dialog_data["product_filter"] = "available"

        if filter_type == "available":
            # Фильтруем предметы, доступные пользователю
            filtered_products = [p for p in products if p[4] <= user_balance]
        else:  # "Все предметы"
            filtered_products = products

        return {
            "products": filtered_products,
            "user_balance": user_balance,
            "product_filter": filter_type,
            "is_user": True,
            "division_radio_data": division_radio_data,
        }

    # Для администраторов/ГОК/МИП - фильтруем по подразделению
    else:
        # Проверяем текущий выбор фильтра подразделения
        selected_division = dialog_manager.dialog_data.get("product_filter", "all")

        # Устанавливаем стандартный фильтр если не установлено иное
        if "product_filter" not in dialog_manager.dialog_data:
            dialog_manager.dialog_data["product_filter"] = "all"
            selected_division = "all"

        # Фильтруем по подразделению
        if selected_division == "all":
            filtered_products = products
        elif selected_division == "nck":
            filtered_products = [p for p in products if p[5] == "НЦК"]
        elif selected_division == "ntp":
            filtered_products = [p for p in products if p[5] == "НТП"]
        else:
            filtered_products = products

        return {
            "products": filtered_products,
            "user_balance": user_balance,
            "product_filter": selected_division,
            "is_user": False,
            "division_radio_data": division_radio_data,
        }

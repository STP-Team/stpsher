from aiogram_dialog import DialogManager

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.misc.states.dialogs.user import UserSG


async def on_product_click(
    callback, widget, dialog_manager: DialogManager, item_id, **kwargs
):
    """
    Обработчик нажатия на продукт - переход к подтверждению покупки
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user = dialog_manager.middleware_data["user"]

    try:
        product_info = await stp_repo.product.get_product(item_id)
    except Exception as e:
        print(e)
        await callback.answer(
            "❌ Ошибка получения информации о предмете", show_alert=True
        )
        return

    # Получаем баланс пользователя
    user_balance = await stp_repo.transaction.get_user_balance(user.user_id)

    # Проверяем, достаточно ли баллов
    if user_balance < product_info.cost:
        await callback.answer(
            f"❌ Недостаточно баллов!\nУ тебя: {user_balance} баллов\nНужно: {product_info.cost} баллов",
            show_alert=True,
        )
        return

    # Сохраняем информацию о выбранном продукте в dialog_data
    dialog_manager.dialog_data["selected_product"] = {
        "id": product_info.id,
        "name": product_info.name,
        "description": product_info.description,
        "cost": product_info.cost,
        "count": product_info.count,
    }
    dialog_manager.dialog_data["user_balance"] = user_balance

    # Переходим к окну подтверждения
    await dialog_manager.switch_to(UserSG.game_shop_confirm)


async def on_confirm_purchase(
    callback, widget, dialog_manager: DialogManager, **kwargs
):
    """
    Обработчик подтверждения покупки
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user = dialog_manager.middleware_data["user"]
    product_info = dialog_manager.dialog_data["selected_product"]

    # Получаем актуальный баланс пользователя
    user_balance = await stp_repo.transaction.get_user_balance(user.user_id)

    if user_balance < product_info["cost"]:
        await callback.answer(
            f"❌ Недостаточно баллов!\nУ тебя: {user_balance}, нужно: {product_info['cost']}",
            show_alert=True,
        )
        return

    try:
        # Создаем покупку со статусом "stored"
        new_purchase = await stp_repo.purchase.add_purchase(
            user_id=user.user_id, product_id=product_info["id"], status="stored"
        )
        await stp_repo.transaction.add_transaction(
            user_id=user.user_id,
            transaction_type="spend",
            source_type="product",
            source_id=product_info["id"],
            amount=product_info["cost"],
            comment=f"Автоматическая покупка предмета {product_info['name']}",
        )

        # Сохраняем информацию о покупке
        dialog_manager.dialog_data["new_purchase"] = {"id": new_purchase.id}
        dialog_manager.dialog_data["new_balance"] = user_balance - product_info["cost"]

        # Переходим к окну успешной покупки
        await dialog_manager.switch_to(UserSG.game_shop_success)

    except Exception:
        await callback.answer("❌ Ошибка при покупке предмета", show_alert=True)


async def on_sell_product(callback, widget, dialog_manager: DialogManager, **kwargs):
    """
    Обработчик продажи предмета
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user = dialog_manager.middleware_data["user"]
    new_purchase = dialog_manager.dialog_data["new_purchase"]
    product_info = dialog_manager.dialog_data["selected_product"]

    try:
        success = await stp_repo.purchase.delete_user_purchase(new_purchase["id"])
        await stp_repo.transaction.add_transaction(
            user_id=user.user_id,
            transaction_type="earn",
            source_type="product",
            source_id=product_info["id"],
            amount=product_info["cost"],
            comment=f"Возврат предмета: {product_info['name']}",
        )

        if success:
            await callback.answer(
                f"✅ Продано: {product_info['name']}.\nВозвращено: {product_info['cost']} баллов"
            )
            # Возвращаемся в магазин
            await dialog_manager.switch_to(UserSG.game_shop)
        else:
            await callback.answer("❌ Ошибка при продаже предмета", show_alert=True)

    except Exception:
        await callback.answer("❌ Ошибка при продаже предмета", show_alert=True)

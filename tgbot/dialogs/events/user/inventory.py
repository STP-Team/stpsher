"""Обработчики операций с инвентарем сотрудников."""

import logging

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, Select

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.misc.states.dialogs.user import UserSG

logger = logging.getLogger(__name__)


async def on_inventory_product_click(
    callback: CallbackQuery,
    _widget: Select,
    dialog_manager: DialogManager,
    item_id,
    **_kwargs,
) -> None:
    """Обработчик перехода к детальному просмотру информации о предмете из инвентаря.

    Args:
        callback: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
        item_id: Идентификатор предмета в инвентаре
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]

    try:
        user_product_detail = await stp_repo.purchase.get_purchase_details(item_id)
    except Exception as e:
        print(e)
        await callback.answer(
            "❌ Ошибка получения информации о предмете", show_alert=True
        )
        return

    if not user_product_detail:
        await callback.answer("❌ Предмет не найден", show_alert=True)
        return

    # Сохраняем информацию о выбранном предмете из инвентаря в dialog_data
    user_product = user_product_detail.user_purchase
    product_info = user_product_detail.product_info

    dialog_manager.dialog_data["selected_inventory_product"] = {
        "user_product_id": user_product.id,
        "product_name": product_info.name,
        "product_description": product_info.description,
        "product_cost": product_info.cost,
        "product_count": product_info.count,
        "status": user_product.status,
        "usage_count": user_product.usage_count,
        "current_usages": user_product_detail.current_usages,
        "max_usages": user_product_detail.max_usages,
        "bought_at": user_product.bought_at.strftime("%d.%m.%Y в %H:%M"),
        "comment": user_product.comment,
        "updated_by_user_id": user_product.updated_by_user_id,
        "updated_at": user_product.updated_at.strftime("%d.%m.%Y в %H:%M")
        if user_product.updated_at
        else None,
    }

    # Переходим к окну детального просмотра предмета инвентаря
    await dialog_manager.switch_to(UserSG.game_inventory_detail)


async def use_product(
    callback: CallbackQuery, _widget: Button, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Универсальный обработчик отправки предмета на активацию.

    Обработчик поддерживает использование как из инвентаря, так и из магазина сразу после приобретения предмета

    Args:
        callback: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]

    # Проверяем, откуда вызвана функция - из окна магазина или из инвентаря
    if dialog_manager.current_context().state == UserSG.game_shop_success:
        # Используем данные только что купленного предмета
        new_purchase = dialog_manager.dialog_data["new_purchase"]
        product_info = dialog_manager.dialog_data["selected_product"]
        user_product_id = new_purchase["id"]
        product_name = product_info["name"]
    else:
        # Используем данные предмета из инвентаря
        product_info = dialog_manager.dialog_data["selected_inventory_product"]
        user_product_id = product_info["user_product_id"]
        product_name = product_info["product_name"]

    try:
        success = await stp_repo.purchase.use_purchase(user_product_id)

        if success:
            await callback.answer(
                f"✅ Предмет {product_name} отправлен на рассмотрение!",
                show_alert=True,
            )
            # Обновляем данные предмета и возвращаемся
            if dialog_manager.current_context().state == UserSG.game_shop_success:
                await dialog_manager.switch_to(UserSG.game_products)
            else:
                await dialog_manager.switch_to(UserSG.game_inventory)
        else:
            await callback.answer("❌ Невозможно использовать предмет", show_alert=True)

    except Exception as e:
        logger.error(
            f"[Активация предметов] Ошибка при отправке предмета на активацию: {e}"
        )
        await callback.answer("❌ Ошибка при использовании предмета", show_alert=True)


async def on_inventory_sell_product(
    callback: CallbackQuery, _widget: Button, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Обработчик продажи предмета из инвентаря.

    Args:
        callback: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user = dialog_manager.middleware_data["user"]
    product_info = dialog_manager.dialog_data["selected_inventory_product"]
    user_product_id = product_info["user_product_id"]

    try:
        success = await stp_repo.purchase.delete_user_purchase(user_product_id)
        await stp_repo.transaction.add_transaction(
            user_id=user.user_id,
            transaction_type="earn",
            source_type="product",
            source_id=user_product_id,  # Используем user_product_id как source_id
            amount=product_info["product_cost"],
            comment=f"Возврат предмета: {product_info['product_name']}",
        )

        if success:
            await callback.answer(
                f"✅ Продано: {product_info['product_name']}.\nВозвращено: {product_info['product_cost']} баллов"
            )
            # Возвращаемся к инвентарю
            await dialog_manager.switch_to(UserSG.game_inventory)
        else:
            await callback.answer("❌ Ошибка при продаже предмета", show_alert=True)

    except Exception as e:
        logger.error(f"[Продажа предмета] Произошла ошибка при продаже предмета: {e}")
        await callback.answer("❌ Ошибка при продаже предмета", show_alert=True)


async def on_inventory_cancel_activation(
    callback: CallbackQuery, _widget: Button, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Обработчик отмены активации предмета из инвентаря.

    Args:
        callback: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    product_info = dialog_manager.dialog_data["selected_inventory_product"]
    user_product_id = product_info["user_product_id"]

    try:
        # Меняем статус обратно на "stored"
        success = await stp_repo.purchase.update_purchase(
            purchase_id=user_product_id, status="stored"
        )

        if success:
            await callback.answer(
                f"✅ Активация предмета '{product_info['product_name']}' отменена!"
            )
            # Возвращаемся к инвентарю
            await dialog_manager.switch_to(UserSG.game_inventory)
        else:
            await callback.answer("❌ Ошибка при отмене активации", show_alert=True)

    except Exception as e:
        logger.error(f"[Активация предметов] Ошибка при отмене активации предмета: {e}")
        await callback.answer("❌ Ошибка при отмене активации", show_alert=True)

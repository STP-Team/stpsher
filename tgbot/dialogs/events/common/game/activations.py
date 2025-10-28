"""Обработчики событий активации предметов."""

import logging

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.api.internal import Widget
from aiogram_dialog.widgets.input import ManagedTextInput
from stp_database import Employee, MainRequestsRepo

from tgbot.dialogs.states.common.game import Game
from tgbot.misc.helpers import format_fullname, strftime_date

logger = logging.getLogger(__name__)


async def on_activation_click(
    callback: CallbackQuery, _widget: Widget, dialog_manager: DialogManager, item_id
) -> None:
    """Обработчик нажатия на предмет в меню активации предмета.

    Args:
        callback: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
        item_id: Идентификатор выбранного варианта
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]

    try:
        # Получаем детальную информацию о покупке
        purchase_details = await stp_repo.purchase.get_purchase_details(item_id)

        if not purchase_details:
            await callback.answer("❌ Покупка не найдена", show_alert=True)
            return

        purchase = purchase_details.user_purchase
        product = purchase_details.product_info

        # Получаем информацию о пользователе
        purchase_user: Employee = await stp_repo.employee.get_users(
            user_id=purchase.user_id
        )
        purchase_user_head: Employee = (
            await stp_repo.employee.get_users(fullname=purchase_user.head)
            if purchase_user and purchase_user.head
            else None
        )

        user_info = format_fullname(
            purchase_user.fullname,
            True,
            True,
            purchase_user.username,
            purchase_user.user_id,
        )

        head_info = format_fullname(
            purchase_user_head.fullname,
            True,
            True,
            purchase_user_head.username,
            purchase_user_head.user_id,
        )

        # Сохраняем информацию о выбранной активации в dialog_data
        dialog_manager.dialog_data["selected_activation"] = {
            "purchase_id": purchase.id,
            "product_name": product.name,
            "product_description": product.description,
            "product_cost": product.cost,
            "product_count": product.count,
            "product_division": product.division,
            "bought_at": purchase.bought_at.strftime(strftime_date),
            "usage_count": purchase.usage_count,
            "user_name": user_info,
            "fullname": purchase_user.fullname,
            "user_division": purchase_user.division if purchase_user else "Неизвестно",
            "user_position": purchase_user.position if purchase_user else "Неизвестно",
            "user_head": head_info,
            "user_username": purchase_user.username if purchase_user else None,
            "user_id": purchase_user.user_id if purchase_user else purchase.user_id,
            "user_comment": purchase.user_comment,
        }

        # Переходим к детальному просмотру
        await dialog_manager.switch_to(Game.activation_details)

    except Exception as e:
        logger.error(
            f"[Активация предметов] Ошибка при просмотре подробностей об активации предмета: {e}"
        )
        await callback.answer(
            "❌ Ошибка получения информации об активации", show_alert=True
        )


async def on_activation_approve_comment_input(
    message: Message,
    _widget: ManagedTextInput,
    dialog_manager: DialogManager,
    comment: str,
) -> None:
    """Обработчик ввода комментария менеджера при одобрении активации.

    Args:
        message: Message от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
        comment: Текст комментария от менеджера
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user: Employee = dialog_manager.middleware_data["user"]
    activation_info = dialog_manager.dialog_data["selected_activation"]

    try:
        # Подтверждаем активацию с комментарием
        await stp_repo.purchase.approve_purchase_usage(
            purchase_id=activation_info["purchase_id"],
            updated_by_user_id=user.user_id,
        )

        # Обновляем комментарий менеджера
        await stp_repo.purchase.update_purchase(
            purchase_id=activation_info["purchase_id"],
            manager_comment=comment,
        )

        await message.answer(
            f"✅ Предмет '{activation_info['product_name']}' активирован с комментарием!\n\nСпециалист {activation_info['fullname']} был уведомлен"
        )

        # Уведомляем пользователя
        if activation_info["usage_count"] + 1 >= activation_info["product_count"]:
            employee_notify_message = f"""<b>👌 Предмет активирован:</b> {activation_info["product_name"]}

Менеджер {format_fullname(user.fullname, True, True, user.username, user.user_id)} подтвердил активацию предмета

💬 <b>Комментарий менеджера:</b>
<blockquote expandable>{comment}</blockquote>

У <b>{activation_info["product_name"]}</b> не осталось использований

<i>Купить его повторно можно в <b>💎 Магазине</b></i>"""
        else:
            remaining_uses = activation_info["product_count"] - (
                activation_info["usage_count"] + 1
            )
            employee_notify_message = f"""<b>👌 Предмет активирован:</b> {activation_info["product_name"]}

Менеджер {format_fullname(user.fullname, True, True, user.username, user.user_id)} подтвердил активацию предмета

💬 <b>Комментарий менеджера:</b>
<blockquote expandable>{comment}</blockquote>

📍 Осталось активаций: {remaining_uses} из {activation_info["product_count"]}"""

        await message.bot.send_message(
            chat_id=activation_info["user_id"],
            text=employee_notify_message,
        )

        # Возвращаемся к списку активаций
        await dialog_manager.switch_to(Game.activations)

    except Exception as e:
        logger.error(
            f"[Активация предметов] Ошибка при подтверждении активации предмета: {e}"
        )
        await message.answer("❌ Ошибка при подтверждении активации")


async def on_skip_approve_comment(
    callback: CallbackQuery, _widget: Widget, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Обработчик пропуска комментария при одобрении активации.

    Args:
        callback: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user: Employee = dialog_manager.middleware_data["user"]
    activation_info = dialog_manager.dialog_data["selected_activation"]

    try:
        # Подтверждаем активацию без комментария
        await stp_repo.purchase.approve_purchase_usage(
            purchase_id=activation_info["purchase_id"],
            updated_by_user_id=user.user_id,
        )

        await callback.answer(
            f"✅ Предмет '{activation_info['product_name']}' активирован!\n\nСпециалист {activation_info['fullname']} был уведомлен",
            show_alert=True,
        )

        # Уведомляем пользователя
        if activation_info["usage_count"] + 1 >= activation_info["product_count"]:
            employee_notify_message = f"""<b>👌 Предмет активирован:</b> {activation_info["product_name"]}

Менеджер {format_fullname(user.fullname, True, True, user.username, user.user_id)} подтвердил активацию предмета

У <b>{activation_info["product_name"]}</b> не осталось использований

<i>Купить его повторно можно в <b>💎 Магазине</b></i>"""
        else:
            remaining_uses = activation_info["product_count"] - (
                activation_info["usage_count"] + 1
            )
            employee_notify_message = f"""<b>👌 Предмет активирован:</b> {activation_info["product_name"]}

Менеджер {format_fullname(user.fullname, True, True, user.username, user.user_id)} подтвердил активацию предмета

📍 Осталось активаций: {remaining_uses} из {activation_info["product_count"]}"""

        await callback.bot.send_message(
            chat_id=activation_info["user_id"],
            text=employee_notify_message,
        )

        # Возвращаемся к списку активаций
        await dialog_manager.switch_to(Game.activations)

    except Exception as e:
        logger.error(
            f"[Активация предметов] Ошибка при подтверждении активации предмета: {e}"
        )
        await callback.answer("❌ Ошибка при подтверждении активации", show_alert=True)


async def on_activation_reject_comment_input(
    message: Message,
    _widget: ManagedTextInput,
    dialog_manager: DialogManager,
    comment: str,
) -> None:
    """Обработчик ввода комментария менеджера при отклонении активации.

    Args:
        message: Message от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
        comment: Текст комментария от менеджера
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user: Employee = dialog_manager.middleware_data["user"]
    activation_info = dialog_manager.dialog_data["selected_activation"]

    try:
        # Отклоняем активацию с комментарием
        await stp_repo.purchase.reject_purchase_usage(
            purchase_id=activation_info["purchase_id"],
            updated_by_user_id=user.user_id,
        )

        # Обновляем комментарий менеджера
        await stp_repo.purchase.update_purchase(
            purchase_id=activation_info["purchase_id"],
            manager_comment=comment,
        )

        await message.answer(
            f"❌ Активация предмета '{activation_info['product_name']}' отклонена с комментарием\n\nСпециалист {activation_info['fullname']} был уведомлен"
        )

        # Уведомляем пользователя
        employee_notify_message = f"""<b>Активация отменена:</b> {activation_info["product_name"]}

Менеджер {format_fullname(user.fullname, True, True, user.username, user.user_id)} отменил активацию <b>{activation_info["product_name"]}</b>

💬 <b>Комментарий менеджера:</b>
<blockquote expandable>{comment}</blockquote>

<i>Использование предмета не будет засчитано</i>"""

        await message.bot.send_message(
            chat_id=activation_info["user_id"],
            text=employee_notify_message,
        )

        # Возвращаемся к списку активаций
        await dialog_manager.switch_to(Game.activations)

    except Exception as e:
        logger.error(f"[Активация предметов] Ошибка при отмене активации предмета: {e}")
        await message.answer("❌ Ошибка при отклонении активации")


async def on_skip_reject_comment(
    callback: CallbackQuery, _widget: Widget, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Обработчик пропуска комментария при отклонении активации.

    Args:
        callback: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user: Employee = dialog_manager.middleware_data["user"]
    activation_info = dialog_manager.dialog_data["selected_activation"]

    try:
        # Отклоняем активацию без комментария
        await stp_repo.purchase.reject_purchase_usage(
            purchase_id=activation_info["purchase_id"],
            updated_by_user_id=user.user_id,
        )

        await callback.answer(
            f"❌ Активация предмета '{activation_info['product_name']}' отклонена\n\nСпециалист {activation_info['fullname']} был уведомлен",
            show_alert=True,
        )

        # Уведомляем пользователя
        employee_notify_message = f"""<b>Активация отменена:</b> {activation_info["product_name"]}

Менеджер {format_fullname(user.fullname, True, True, user.username, user.user_id)} отменил активацию <b>{activation_info["product_name"]}</b>

<i>Использование предмета не будет засчитано</i>"""

        await callback.bot.send_message(
            chat_id=activation_info["user_id"],
            text=employee_notify_message,
        )

        # Возвращаемся к списку активаций
        await dialog_manager.switch_to(Game.activations)

    except Exception as e:
        logger.error(f"[Активация предметов] Ошибка при отмене активации предмета: {e}")
        await callback.answer("❌ Ошибка при отклонении активации", show_alert=True)

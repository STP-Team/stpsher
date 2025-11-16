"""Обработчики событий активации предметов."""

import logging

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.api.internal import Widget
from aiogram_dialog.widgets.input import ManagedTextInput
from stp_database import Employee, MainRequestsRepo
from stp_database.repo.STP.purchase import PurchaseDetailedParams

from tgbot.dialogs.states.common.game import Game
from tgbot.misc.helpers import format_fullname

logger = logging.getLogger(__name__)


async def on_activation_click(
    _event: CallbackQuery, _widget: Widget, dialog_manager: DialogManager, item_id
) -> None:
    """Обработчик нажатия на предмет в меню активации предмета.

    Args:
        _event: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
        item_id: Идентификатор выбранного варианта
    """
    dialog_manager.dialog_data["purchase_id"] = item_id

    # Переходим к детальному просмотру
    await dialog_manager.switch_to(Game.activation_details)


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
    purchase_id = dialog_manager.dialog_data["purchase_id"]
    purchase: PurchaseDetailedParams = await stp_repo.purchase.get_purchase_details(
        purchase_id
    )

    try:
        # Подтверждаем активацию с комментарием
        await stp_repo.purchase.approve_purchase_usage(
            purchase_id=purchase_id,
            updated_by_user_id=user.user_id,
        )

        # Обновляем комментарий менеджера
        await stp_repo.purchase.update_purchase(
            purchase_id=purchase_id,
            manager_comment=comment,
        )

        await message.answer(
            f"✅ Предмет '{purchase.product_info.name}' активирован с комментарием!\n\nСпециалист был уведомлен об активации"
        )

        # Уведомляем пользователя
        if purchase.user_purchase.usage_count + 1 >= purchase.product_info.count:
            employee_notify_message = f"""<b>👌 Предмет активирован:</b> {purchase.product_info.name}

Менеджер {format_fullname(user, True, True)} подтвердил активацию предмета

💬 <b>Комментарий менеджера:</b>
<blockquote expandable>{comment}</blockquote>

У <b>{purchase.product_info.name}</b> не осталось использований

<i>Купить его повторно можно в <b>💎 Магазине</b></i>"""
        else:
            remaining_uses = purchase.product_info.count - (
                purchase.user_purchase.usage_count + 1
            )
            employee_notify_message = f"""<b>👌 Предмет активирован:</b> {purchase.product_info.name}

Менеджер {format_fullname(user, True, True)} подтвердил активацию предмета

💬 <b>Комментарий менеджера:</b>
<blockquote expandable>{comment}</blockquote>

📍 Осталось активаций: {remaining_uses} из {purchase.product_info.count}"""

        await message.bot.send_message(
            chat_id=purchase.user_purchase.user_id,
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
    event: CallbackQuery, _widget: Widget, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Обработчик пропуска комментария при одобрении активации.

    Args:
        event: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user: Employee = dialog_manager.middleware_data["user"]
    purchase_id = dialog_manager.dialog_data["purchase_id"]
    purchase: PurchaseDetailedParams = await stp_repo.purchase.get_purchase_details(
        purchase_id
    )

    try:
        # Подтверждаем активацию без комментария
        await stp_repo.purchase.approve_purchase_usage(
            purchase_id=purchase.user_purchase.id,
            updated_by_user_id=user.user_id,
        )

        await event.answer(
            f"✅ Предмет '{purchase.product_info.name}' активирован!\n\nСпециалист был уведомлен об активации",
            show_alert=True,
        )

        # Уведомляем пользователя
        if purchase.user_purchase.usage_count + 1 >= purchase.product_info.count:
            employee_notify_message = f"""<b>👌 Предмет активирован:</b> {purchase.product_info.name}

Менеджер {format_fullname(user, True, True)} подтвердил активацию предмета

У <b>{purchase.product_info.name}</b> не осталось использований

<i>Купить его повторно можно в <b>💎 Магазине</b></i>"""
        else:
            remaining_uses = purchase.product_info.count - (
                purchase.user_purchase.usage_count + 1
            )
            employee_notify_message = f"""<b>👌 Предмет активирован:</b> {purchase.product_info.name}

Менеджер {format_fullname(user, True, True)} подтвердил активацию предмета

📍 Осталось активаций: {remaining_uses} из {purchase.product_info.count}"""

        await event.bot.send_message(
            chat_id=purchase.user_purchase.user_id,
            text=employee_notify_message,
        )

        # Возвращаемся к списку активаций
        await dialog_manager.switch_to(Game.activations)

    except Exception as e:
        logger.error(
            f"[Активация предметов] Ошибка при подтверждении активации предмета: {e}"
        )
        await event.answer("❌ Ошибка при подтверждении активации", show_alert=True)


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
    purchase_id = dialog_manager.dialog_data["purchase_id"]
    purchase: PurchaseDetailedParams = await stp_repo.purchase.get_purchase_details(
        purchase_id
    )

    try:
        # Отклоняем активацию с комментарием
        await stp_repo.purchase.reject_purchase_usage(
            purchase_id=purchase_id,
            updated_by_user_id=user.user_id,
        )

        # Обновляем комментарий менеджера
        await stp_repo.purchase.update_purchase(
            purchase_id=purchase_id,
            manager_comment=comment,
        )

        await message.answer(
            f"❌ Активация предмета '{purchase.product_info.name}' отклонена с комментарием\n\nСпециалист был уведомлен"
        )

        # Уведомляем пользователя
        employee_notify_message = f"""<b>Активация отменена:</b> {purchase.product_info.name}

Менеджер {format_fullname(user, True, True)} отменил активацию <b>{purchase.product_info.name}</b>

💬 <b>Комментарий менеджера:</b>
<blockquote expandable>{comment}</blockquote>

<i>Использование предмета не будет засчитано</i>"""

        await message.bot.send_message(
            chat_id=purchase.user_purchase.user_id,
            text=employee_notify_message,
        )

        # Возвращаемся к списку активаций
        await dialog_manager.switch_to(Game.activations)

    except Exception as e:
        logger.error(f"[Активация предметов] Ошибка при отмене активации предмета: {e}")
        await message.answer("❌ Ошибка при отклонении активации")


async def on_skip_reject_comment(
    event: CallbackQuery, _widget: Widget, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Обработчик пропуска комментария при отклонении активации.

    Args:
        event: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user: Employee = dialog_manager.middleware_data["user"]
    purchase_id = dialog_manager.dialog_data["purchase_id"]
    purchase: PurchaseDetailedParams = await stp_repo.purchase.get_purchase_details(
        purchase_id
    )

    try:
        # Отклоняем активацию без комментария
        await stp_repo.purchase.reject_purchase_usage(
            purchase_id=purchase_id,
            updated_by_user_id=user.user_id,
        )

        await event.answer(
            f"❌ Активация предмета '{purchase.product_info.name}' отклонена\n\nСпециалист был уведомлен",
            show_alert=True,
        )

        # Уведомляем пользователя
        employee_notify_message = f"""<b>Активация отменена:</b> {purchase.product_info.name}

Менеджер {format_fullname(user, True, True)} отменил активацию <b>{purchase.product_info.name}</b>

<i>Использование предмета не будет засчитано</i>"""

        await event.bot.send_message(
            chat_id=purchase.user_purchase.user_id,
            text=employee_notify_message,
        )

        # Возвращаемся к списку активаций
        await dialog_manager.switch_to(Game.activations)

    except Exception as e:
        logger.error(f"[Активация предметов] Ошибка при отмене активации предмета: {e}")
        await event.answer("❌ Ошибка при отклонении активации", show_alert=True)

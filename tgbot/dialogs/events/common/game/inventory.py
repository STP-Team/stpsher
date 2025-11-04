"""Обработчики операций с инвентарем сотрудников."""

import logging
from datetime import datetime

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.kbd import Button, Select
from stp_database import MainRequestsRepo

from tgbot.dialogs.states.common.game import Game
from tgbot.misc.helpers import strftime_date, tz
from tgbot.services.broadcaster import broadcast
from tgbot.services.files_processing.parsers.schedule import DutyScheduleParser
from tgbot.services.mailing import (
    send_activation_product_email,
    send_cancel_product_email,
)

logger = logging.getLogger(__name__)


async def on_inventory_product_click(
    event: CallbackQuery,
    _widget: Select,
    dialog_manager: DialogManager,
    item_id,
    **_kwargs,
) -> None:
    """Обработчик перехода к детальному просмотру информации о предмете из инвентаря.

    Args:
        event: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
        item_id: Идентификатор предмета в инвентаре
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]

    try:
        user_product_detail = await stp_repo.purchase.get_purchase_details(item_id)
    except Exception:
        await event.answer("❌ Ошибка получения информации о предмете", show_alert=True)
        return

    if not user_product_detail:
        await event.answer("❌ Предмет не найден", show_alert=True)
        return

    # Сохраняем информацию о выбранном предмете из инвентаря в dialog_data
    user_product = user_product_detail.user_purchase
    product_info = user_product_detail.product_info

    dialog_manager.dialog_data["selected_inventory_product"] = {
        "user_product_id": user_product.id,
        "product_id": product_info.id,
        "product_name": product_info.name,
        "product_description": product_info.description,
        "product_cost": product_info.cost,
        "product_count": product_info.count,
        "activate_days": product_info.activate_days,
        "status": user_product.status,
        "usage_count": user_product.usage_count,
        "current_usages": user_product_detail.current_usages,
        "max_usages": user_product_detail.max_usages,
        "bought_at": user_product.bought_at.strftime(strftime_date),
        "comment": user_product.user_comment,
        "updated_by_user_id": user_product.updated_by_user_id,
        "updated_at": user_product.updated_at.strftime(strftime_date)
        if user_product.updated_at
        else None,
    }

    # Переходим к окну детального просмотра предмета инвентаря
    await dialog_manager.switch_to(Game.inventory_details)


async def use_product(
    event: CallbackQuery, _widget: Button, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Универсальный обработчик отправки предмета на активацию.

    Обработчик поддерживает использование как из инвентаря, так и из магазина сразу после приобретения предмета

    Args:
        event: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
    """
    # Проверяем, откуда вызвана функция - из окна магазина или из инвентаря
    if dialog_manager.current_context().state == Game.products_success:
        # Используем данные только что купленного предмета
        product_info = dialog_manager.dialog_data["selected_product"]
        product_name = product_info["name"]
        activate_days = product_info.get("activate_days")
    else:
        # Используем данные предмета из инвентаря
        product_info = dialog_manager.dialog_data["selected_inventory_product"]
        product_name = product_info["product_name"]
        activate_days = product_info.get("activate_days")

    try:
        # Проверяем ограничения дня активации предмета
        if activate_days is not None and len(activate_days) > 0:
            current_day = datetime.now(tz).day

            if current_day not in activate_days:
                # Форматируем список доступных дней
                days_str = ", ".join(str(day) for day in sorted(activate_days))
                await event.answer(
                    f"❌ Предмет '{product_name}' нельзя активировать сегодня.\n"
                    f"Доступные дни месяца: {days_str}",
                    show_alert=True,
                )
                return

        # Если все проверки пройдены, переходим к окну комментария
        if dialog_manager.current_context().state == Game.products_success:
            # Для магазина используем старую логику (без комментария)
            stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
            new_purchase = dialog_manager.dialog_data["new_purchase"]
            user_product_id = new_purchase["id"]

            success = await stp_repo.purchase.use_purchase(user_product_id)

            if success:
                await event.answer(
                    f"✅ Предмет {product_name} отправлен на рассмотрение!",
                    show_alert=True,
                )
                await dialog_manager.switch_to(Game.products)
            else:
                await event.answer(
                    "❌ Невозможно использовать предмет", show_alert=True
                )
        else:
            # Для инвентаря переходим к окну ввода комментария
            await dialog_manager.switch_to(Game.inventory_activation_comment)

    except Exception as e:
        logger.error(
            f"[Активация предметов] Ошибка при отправке предмета на активацию: {e}"
        )
        await event.answer("❌ Ошибка при использовании предмета", show_alert=True)


async def on_inventory_activation_comment_input(
    message: Message,
    _widget: ManagedTextInput,
    dialog_manager: DialogManager,
    comment: str,
) -> None:
    """Обработчик ввода комментария пользователя при активации предмета.

    Args:
        message: Message от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
        comment: Текст комментария от пользователя
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user = dialog_manager.middleware_data["user"]
    product_info = dialog_manager.dialog_data["selected_inventory_product"]
    user_product_id = product_info["user_product_id"]
    product_name = product_info["product_name"]

    try:
        # Обновляем статус покупки и добавляем комментарий
        await stp_repo.purchase.update_purchase(
            purchase_id=user_product_id,
            status="review",
            user_comment=comment,
            updated_at=datetime.now(tz),
        )

        # Получаем полную информацию о предмете и покупке для отправки email
        user_product_detail = await stp_repo.purchase.get_purchase_details(
            user_product_id
        )

        if user_product_detail:
            product = user_product_detail.product_info
            purchase = user_product_detail.user_purchase

            # Получаем руководителя пользователя
            user_head = None
            if user.head:
                user_head = await stp_repo.employee.get_users(fullname=user.head)

            # Получаем текущего дежурного
            current_duty_user = None
            if user_head:
                duty_scheduler = DutyScheduleParser()
                current_duty = await duty_scheduler.get_current_senior_duty(
                    division=str(user_head.division), stp_repo=stp_repo
                )
                if current_duty:
                    current_duty_user = await stp_repo.employee.get_users(
                        user_id=current_duty.user_id
                    )

            # Отправляем email уведомление
            bot_info = await message.bot.get_me()
            await send_activation_product_email(
                user,
                user_head,
                current_duty_user,
                product,
                purchase,
                bot_username=bot_info.username,
            )

            # Определяем получателей уведомлений
            manager_ids = []
            manager_role = product.manager_role

            if manager_role == 3:
                # Для manager_role 3 уведомляем только текущих дежурных
                duty_scheduler = DutyScheduleParser()
                current_senior = await duty_scheduler.get_current_senior_duty(
                    user.division, stp_repo
                )
                current_helper = await duty_scheduler.get_current_helper_duty(
                    user.division, stp_repo
                )

                if current_senior and current_senior.user_id != user.user_id:
                    manager_ids.append(current_senior.user_id)
                if current_helper and current_helper.user_id != user.user_id:
                    manager_ids.append(current_helper.user_id)
            elif manager_role in [5, 6]:
                # Для manager_role 5 или 6 уведомляем пользователей с такой же ролью
                users_with_role = await stp_repo.employee.get_users(roles=manager_role)
                for role_user in users_with_role:
                    if role_user.user_id != user.user_id:
                        manager_ids.append(role_user.user_id)

            # Отправляем уведомления менеджерам
            if manager_ids:
                notification_text = f"""<b>🔔 Новый предмет на активацию</b>

<b>🛒 Предмет:</b> {product_name}
<b>👤 Заявитель:</b> <a href='t.me/{user.username}'>{user.fullname}</a>
<b>📋 Описание:</b> {product.description}
{f"<b>💬 Комментарий:</b>\n<blockquote expandable{comment}</blockquote>" if comment else ""}

<b>Требуется рассмотрение заявки</b>"""

                result = await broadcast(
                    bot=message.bot,
                    users=manager_ids,
                    text=notification_text,
                )

                logger.info(
                    f"[Использование предмета] {user.username} ({user.user_id}) отправил на рассмотрение '{product_name}'. Уведомлено менеджеров: {result} из {len(manager_ids)}"
                )

        await message.answer(
            f"✅ Предмет {product_name} отправлен на рассмотрение с комментарием!"
        )
        await dialog_manager.switch_to(Game.inventory)

    except Exception as e:
        logger.error(f"[Активация предметов] Ошибка при сохранении комментария: {e}")
        await message.answer("❌ Ошибка при сохранении комментария")


async def on_skip_activation_comment(
    event: CallbackQuery, _widget: Button, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Обработчик пропуска комментария при активации предмета.

    Args:
        event: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user = dialog_manager.middleware_data["user"]
    product_info = dialog_manager.dialog_data["selected_inventory_product"]
    user_product_id = product_info["user_product_id"]
    product_name = product_info["product_name"]

    try:
        # Активируем без комментария
        success = await stp_repo.purchase.use_purchase(user_product_id)

        if success:
            # Получаем полную информацию о предмете и покупке для отправки email
            user_product_detail = await stp_repo.purchase.get_purchase_details(
                user_product_id
            )

            if user_product_detail:
                product = user_product_detail.product_info
                purchase = user_product_detail.user_purchase

                # Получаем руководителя пользователя
                user_head = None
                if user.head:
                    user_head = await stp_repo.employee.get_users(fullname=user.head)

                # Получаем текущего дежурного
                current_duty_user = None
                if user_head:
                    duty_scheduler = DutyScheduleParser()
                    current_duty = await duty_scheduler.get_current_senior_duty(
                        division=str(user_head.division), stp_repo=stp_repo
                    )
                    if current_duty:
                        current_duty_user = await stp_repo.employee.get_users(
                            user_id=current_duty.user_id
                        )

                # Отправляем email уведомление
                bot_info = await event.bot.get_me()
                await send_activation_product_email(
                    user,
                    user_head,
                    current_duty_user,
                    product,
                    purchase,
                    bot_username=bot_info.username,
                )

                # Определяем получателей уведомлений
                manager_ids = []
                manager_role = product.manager_role

                if manager_role == 3:
                    # Для manager_role 3 уведомляем только текущих дежурных
                    duty_scheduler = DutyScheduleParser()
                    current_senior = await duty_scheduler.get_current_senior_duty(
                        user.division, stp_repo
                    )
                    current_helper = await duty_scheduler.get_current_helper_duty(
                        user.division, stp_repo
                    )

                    if current_senior and current_senior.user_id != user.user_id:
                        manager_ids.append(current_senior.user_id)
                    if current_helper and current_helper.user_id != user.user_id:
                        manager_ids.append(current_helper.user_id)
                elif manager_role in [5, 6]:
                    # Для manager_role 5 или 6 уведомляем пользователей с такой же ролью
                    users_with_role = await stp_repo.employee.get_users(
                        roles=manager_role
                    )
                    for role_user in users_with_role:
                        if role_user.user_id != user.user_id:
                            manager_ids.append(role_user.user_id)

                # Отправляем уведомления менеджерам
                if manager_ids:
                    notification_text = f"""<b>🔔 Новый предмет на активацию</b>

<b>🛒 Предмет:</b> {product_name}
<b>👤 Заявитель:</b> <a href='t.me/{user.username}'>{user.fullname}</a>
<b>📋 Описание:</b> {product.description}

<b>Требуется рассмотрение заявки</b>"""

                    result = await broadcast(
                        bot=event.bot,
                        users=manager_ids,
                        text=notification_text,
                    )

                    logger.info(
                        f"[Использование предмета] {user.username} ({user.user_id}) отправил на рассмотрение '{product_name}'. Уведомлено менеджеров: {result} из {len(manager_ids)}"
                    )

            await event.answer(
                f"✅ Предмет {product_name} отправлен на рассмотрение!",
                show_alert=True,
            )
            await dialog_manager.switch_to(Game.inventory)
        else:
            await event.answer("❌ Невозможно использовать предмет", show_alert=True)

    except Exception as e:
        logger.error(
            f"[Активация предметов] Ошибка при отправке предмета на активацию: {e}"
        )
        await event.answer("❌ Ошибка при использовании предмета", show_alert=True)


async def on_inventory_sell_product(
    event: CallbackQuery, _widget: Button, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Обработчик продажи предмета из инвентаря.

    Args:
        event: Callback query от Telegram
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
            await event.answer(
                f"✅ Продано: {product_info['product_name']}.\nВозвращено: {product_info['product_cost']} баллов"
            )
            # Возвращаемся к инвентарю
            await dialog_manager.switch_to(Game.inventory)
        else:
            await event.answer("❌ Ошибка при продаже предмета", show_alert=True)

    except Exception as e:
        logger.error(f"[Продажа предмета] Произошла ошибка при продаже предмета: {e}")
        await event.answer("❌ Ошибка при продаже предмета", show_alert=True)


async def on_inventory_cancel_activation(
    event: CallbackQuery, _widget: Button, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Обработчик отмены активации предмета из инвентаря.

    Args:
        event: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user = dialog_manager.middleware_data["user"]
    product_info = dialog_manager.dialog_data["selected_inventory_product"]
    user_product_id = product_info["user_product_id"]

    try:
        # Меняем статус обратно на "stored"
        success = await stp_repo.purchase.update_purchase(
            purchase_id=user_product_id, status="stored"
        )

        if success:
            # Получаем полную информацию о предмете и покупке для отправки email
            user_product_detail = await stp_repo.purchase.get_purchase_details(
                user_product_id
            )

            if user_product_detail:
                product = user_product_detail.product_info
                purchase = user_product_detail.user_purchase

                # Получаем руководителя пользователя
                user_head = None
                if user.head:
                    user_head = await stp_repo.employee.get_users(fullname=user.head)

                # Получаем текущего дежурного
                current_duty_user = None
                if user_head:
                    duty_scheduler = DutyScheduleParser()
                    current_duty = await duty_scheduler.get_current_senior_duty(
                        division=str(user_head.division), stp_repo=stp_repo
                    )
                    if current_duty:
                        current_duty_user = await stp_repo.employee.get_users(
                            user_id=current_duty.user_id
                        )

                # Отправляем email уведомление об отмене
                bot_info = await event.bot.get_me()
                await send_cancel_product_email(
                    user,
                    user_head,
                    current_duty_user,
                    product,
                    purchase,
                    bot_username=bot_info.username,
                )

                # Определяем получателей уведомлений
                manager_ids = []
                manager_role = product.manager_role

                if manager_role == 3:
                    # Для manager_role 3 уведомляем только текущих дежурных
                    duty_scheduler = DutyScheduleParser()
                    current_senior = await duty_scheduler.get_current_senior_duty(
                        user.division, stp_repo
                    )
                    current_helper = await duty_scheduler.get_current_helper_duty(
                        user.division, stp_repo
                    )

                    if current_senior and current_senior.user_id != user.user_id:
                        manager_ids.append(current_senior.user_id)
                    if current_helper and current_helper.user_id != user.user_id:
                        manager_ids.append(current_helper.user_id)
                elif manager_role in [5, 6]:
                    # Для manager_role 5 или 6 уведомляем пользователей с такой же ролью
                    users_with_role = await stp_repo.employee.get_users(
                        roles=manager_role
                    )
                    for role_user in users_with_role:
                        if role_user.user_id != user.user_id:
                            manager_ids.append(role_user.user_id)

                # Отправляем уведомления менеджерам (без клавиатуры)
                if manager_ids:
                    notification_text = f"""<b>🔔 Отмена активации предмета</b>

<b>🛒 Предмет:</b> {product.name}
<b>👤 Пользователь:</b> <a href='t.me/{user.username}'>{user.fullname}</a>
<b>📋 Описание:</b> {product.description}

<b>Активация предмета отменена</b>"""

                    result = await broadcast(
                        bot=event.bot,
                        users=manager_ids,
                        text=notification_text,
                    )

                    logger.info(
                        f"[Отмена активации] {user.username} ({user.user_id}) отменил активацию '{product.name}'. Уведомлено менеджеров: {result} из {len(manager_ids)}"
                    )

            await event.answer(
                f"✅ Активация предмета '{product_info['product_name']}' отменена!"
            )
            # Возвращаемся к инвентарю
            await dialog_manager.switch_to(Game.inventory)
        else:
            await event.answer("❌ Ошибка при отмене активации", show_alert=True)

    except Exception as e:
        logger.error(f"[Активация предметов] Ошибка при отмене активации предмета: {e}")
        await event.answer("❌ Ошибка при отмене активации", show_alert=True)

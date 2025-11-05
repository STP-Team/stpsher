"""Сервис для уведомления о совпадениях подписок при создании обменов."""

import logging

from aiogram import Bot
from stp_database import Exchange, MainRequestsRepo

from tgbot.dialogs.getters.common.exchanges.exchanges import get_exchange_text
from tgbot.services.broadcaster import send_message
from tgbot.services.schedulers.exchanges import (
    MESSAGES,
    create_exchange_deeplink,
    create_subscription_deeplink,
    create_subscription_keyboard,
)

logger = logging.getLogger(__name__)


async def find_matching_subscriptions(
    bot: Bot, stp_repo: MainRequestsRepo, exchange: Exchange
) -> int:
    """Находит и уведомляет пользователей с подписками, соответствующими новому обмену.

    Args:
        bot: Экземпляр бота
        stp_repo: Репозиторий операций с базой STP
        exchange: Новый созданный обмен

    Returns:
        Количество отправленных уведомлений
    """
    try:
        # Находим все подписки, соответствующие этому обмену (используем БД для фильтрации)
        matching_subscriptions = await stp_repo.exchange.find_matching_subscriptions(
            exchange
        )

        if not matching_subscriptions:
            return 0

        notifications_sent = 0

        # Отправляем уведомления через broadcaster's send_message
        for subscription in matching_subscriptions:
            try:
                success = await notify_subscription_match(
                    bot, stp_repo, subscription, exchange
                )
                if success:
                    notifications_sent += 1
            except Exception as e:
                logger.error(
                    f"Ошибка отправки уведомления о совпадении подписки {subscription.id}: {e}"
                )

        if notifications_sent > 0:
            logger.info(
                f"Отправлено {notifications_sent} уведомлений о совпадении подписок для обмена {exchange.id}"
            )

        return notifications_sent

    except Exception as e:
        logger.error(f"Ошибка поиска совпадений подписок для обмена {exchange.id}: {e}")
        return 0


async def notify_subscription_match(
    bot: Bot, stp_repo: MainRequestsRepo, subscription, exchange: Exchange
) -> bool:
    """Отправляет уведомление о совпадении подписки.

    Args:
        bot: Экземпляр бота
        stp_repo: Репозиторий базы данных
        subscription: Подписка
        exchange: Экземпляр сделки с моделью Exchange

    Returns:
        True если уведомление отправлено успешно, False иначе
    """
    try:
        # Получаем данные пользователя
        user = await stp_repo.employee.get_users(user_id=subscription.subscriber_id)
        if not user:
            logger.warning(
                f"Не найден пользователь {subscription.subscriber_id} для подписки {subscription.id}"
            )
            return False

        # Формируем информацию об обмене
        exchange_info = await get_exchange_text(
            stp_repo, exchange, user_id=user.user_id
        )

        # Создаем deeplinks
        exchange_deeplink = await create_exchange_deeplink(bot, exchange.id)
        subscription_deeplink = await create_subscription_deeplink(bot, subscription.id)

        # Формируем сообщение
        message_text = MESSAGES["subscription_match"].format(
            subscription_name=subscription.name, exchange_info=exchange_info
        )

        # Создаем клавиатуру
        reply_markup = create_subscription_keyboard(
            exchange_deeplink, subscription_deeplink
        )

        # Отправляем уведомление
        success = await send_message(
            bot=bot,
            user_id=subscription.subscriber_id,
            text=message_text,
            reply_markup=reply_markup,
        )

        if success:
            logger.info(
                f"Отправлено уведомление о совпадении подписки {subscription.id} пользователю {subscription.subscriber_id}"
            )
            return True
        else:
            logger.warning(
                f"Не удалось отправить уведомление о совпадении подписки {subscription.id} пользователю {subscription.subscriber_id}"
            )
            return False

    except Exception as e:
        logger.error(
            f"Ошибка отправки уведомления о совпадении подписки {subscription.id}: {e}"
        )
        return False

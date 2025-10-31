import logging
from datetime import datetime

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.deep_linking import create_start_link
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from stp_database import Exchange, MainRequestsRepo

from tgbot.dialogs.getters.common.exchanges.exchanges import (
    get_exchange_text,
)
from tgbot.misc.helpers import format_fullname, tz
from tgbot.services.schedulers.base import BaseScheduler

logger = logging.getLogger(__name__)


class ExchangesScheduler(BaseScheduler):
    """Планировщик биржи подмен."""

    def __init__(self):
        super().__init__("Биржа подмен")

    def setup_jobs(
        self, scheduler: AsyncIOScheduler, session_pool, bot: Bot, kpi_session_pool=None
    ):
        """Настройка всех задач биржи."""
        self.logger.info("Настройка задач биржи...")

        # Проверка истекших предложений
        scheduler.add_job(
            func=self._check_expired_offers,
            args=[session_pool, bot],
            trigger="interval",
            id="exchanges_check_expired_offers",
            name="Проверка истекших предложений",
            minutes=1,
            coalesce=True,
            misfire_grace_time=300,
            replace_existing=True,
        )

        # Проверка совпадений подписок
        scheduler.add_job(
            func=self._check_subscription_matches,
            args=[session_pool, bot],
            trigger="interval",
            id="exchanges_check_subscription_matches",
            name="Проверка совпадений подписок",
            minutes=2,
            coalesce=True,
            misfire_grace_time=300,
            replace_existing=True,
        )

    async def _check_expired_offers(self, session_pool, bot: Bot):
        """Проверка истекших сделок"""
        await check_expired_offers(session_pool, bot)

    async def _check_subscription_matches(self, session_pool, bot: Bot):
        """Проверка совпадений подписок с новыми обменами"""
        await check_subscription_matches(session_pool, bot)


async def check_expired_offers(session_pool, bot: Bot):
    """Проверка и скрытие истекших сделок.

    Args:
        session_pool: Пул сессий основной БД
        bot: Экземпляр бота
    """
    async with session_pool() as stp_session:
        stp_repo = MainRequestsRepo(stp_session)

        active_exchanges = await stp_repo.exchange.get_active_exchanges(
            include_private=True, limit=200
        )

        current_local_time = datetime.now(tz)

        for exchange in active_exchanges:
            # Определяем время истечения в зависимости от типа предложения
            if exchange.type == "sell":
                # Предложения продажи завершаются когда начинается время предложения
                expiration_datetime = exchange.start_time
            elif exchange.type == "buy":
                # Предложения покупки завершаются когда заканчивается время предложения
                expiration_datetime = exchange.end_time
            else:
                continue

            # Если время истечения не задано, пропускаем
            if expiration_datetime is None:
                continue

            # Приводим время истечения к локальной временной зоне если оно timezone-naive
            if expiration_datetime.tzinfo is None:
                expiration_datetime = tz.localize(expiration_datetime)

            # Проверяем истечение предложения
            if current_local_time >= expiration_datetime:
                await stp_repo.exchange.expire_exchange(exchange.id)
                await notify_expire_offer(bot, stp_repo, exchange)


async def notify_expire_offer(bot: Bot, stp_repo: MainRequestsRepo, exchange: Exchange):
    if exchange.type == "sell":
        owner = await stp_repo.employee.get_users(user_id=exchange.seller_id)
    else:
        owner = await stp_repo.employee.get_users(user_id=exchange.buyer_id)

    owner_name = format_fullname(
        owner.fullname,
        short=True,
        gender_emoji=True,
        username=owner.username,
        user_id=owner.user_id,
    )

    if exchange.payment_type == "immediate":
        payment_info = "Сразу при покупке"
    elif exchange.payment_date:
        payment_info = f"До {exchange.payment_date.strftime('%d.%m.%Y')}"
    else:
        payment_info = "По договоренности"

    exchange_info = await get_exchange_text(exchange, user_id=owner.user_id)
    deeplink = await create_start_link(
        bot=bot, payload=f"exchange_{exchange.id}", encode=True
    )

    await bot.send_message(
        chat_id=exchange.seller_id,
        text=f"""⏳ <b>Сделка истекла</b>

У предложения наступило время {"начала" if exchange.type == "sell" else "конца"}

{exchange_info}

<i>Ты можешь отредактировать его и опубликовать снова</i>""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Открыть сделку", url=deeplink)]
            ]
        ),
    )


async def check_subscription_matches(session_pool, bot: Bot):
    """Проверка новых обменов на совпадения с подписками.

    Args:
        session_pool: Пул сессий основной БД
        bot: Экземпляр бота
    """
    async with session_pool() as stp_session:
        stp_repo = MainRequestsRepo(stp_session)

        try:
            # Получаем новые обмены (созданные за последние 5 минут)
            current_time = datetime.now(tz)
            recent_exchanges = await stp_repo.exchange.get_active_exchanges(
                include_private=False, limit=50
            )

            # Фильтруем обмены, созданные за последние 5 минут
            new_exchanges = []
            for exchange in recent_exchanges:
                if exchange.created_at:
                    # Приводим created_at к локальной временной зоне если оно timezone-naive
                    created_at = exchange.created_at
                    if created_at.tzinfo is None:
                        created_at = tz.localize(created_at)

                    if (current_time - created_at).total_seconds() <= 300:
                        new_exchanges.append(exchange)

            if not new_exchanges:
                return

            for exchange in new_exchanges:
                # Находим все подписки, соответствующие этому обмену
                matching_subscriptions = (
                    await stp_repo.exchange.find_matching_subscriptions(exchange)
                )

                for subscription in matching_subscriptions:
                    # Проверяем, не отправляли ли уже уведомление (пока пропускаем проверку)
                    await notify_subscription_match(
                        bot, stp_repo, subscription, exchange
                    )

        except Exception as e:
            logger.error(f"Ошибка проверки совпадений подписок: {e}")


async def notify_subscription_match(
    bot: Bot, stp_repo: MainRequestsRepo, subscription, exchange: Exchange
):
    """Отправка уведомления о совпадении подписки.

    Args:
        bot: Экземпляр бота
        stp_repo: Репозиторий базы данных
        subscription: Подписка
        exchange: Обмен
    """
    try:
        # Получаем данные пользователя
        user = await stp_repo.employee.get_users(user_id=subscription.subscriber_id)
        if not user:
            return

        # Формируем текст уведомления
        exchange_info = await get_exchange_text(exchange, user_id=user.user_id)

        # Создаем deeplink
        deeplink = await create_start_link(
            bot=bot, payload=f"exchange_{exchange.id}", encode=True
        )

        message_text = f"""🔔 <b>Новый обмен</b>

Найден обмен, соответствующий вашей подписке "{subscription.name}":

{exchange_info}

💰 <b>Цена:</b> {exchange.price} р.
💳 <b>Оплата:</b> {"Сразу" if exchange.payment_type == "immediate" else "По договоренности"}"""

        reply_markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Открыть обмен", url=deeplink)]]
        )

        await bot.send_message(
            chat_id=subscription.subscriber_id,
            text=message_text,
            reply_markup=reply_markup,
            disable_notification=False,
        )

        logger.info(
            f"Отправлено уведомление о совпадении подписки {subscription.id} пользователю {subscription.subscriber_id}"
        )

    except Exception as e:
        logger.error(f"Ошибка отправки уведомления о совпадении: {e}")

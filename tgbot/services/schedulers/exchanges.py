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
            id="achievements_check_daily_achievements",
            name="Проверка истекших предложений",
            minutes=1,
            coalesce=True,
            misfire_grace_time=300,
            replace_existing=True,
        )

    async def _check_expired_offers(self, session_pool, bot: Bot):
        """Проверка истекших сделок"""
        await check_expired_offers(session_pool, bot)


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
        text=f"""⏳ <b>Предложение истекло</b>

У предложения наступило время {"начала" if exchange.type == "sell" else "конца"}

{exchange_info}

<i>Ты можешь отредактировать его и опубликовать снова</i>""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Открыть сделку", url=deeplink)]
            ]
        ),
    )

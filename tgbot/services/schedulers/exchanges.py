import logging
from datetime import datetime

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.deep_linking import create_start_link
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from stp_database import Exchange, MainRequestsRepo

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

        for exchange in active_exchanges:
            shift_date = exchange.shift_date
            shift_time = datetime.strptime(exchange.shift_start_time, "%H:%M").time()
            shift_datetime_local = datetime.combine(shift_date.date(), shift_time)
            shift_datetime_local = tz.localize(shift_datetime_local)
            current_local_time = datetime.now(tz)

            if current_local_time >= shift_datetime_local:
                await stp_repo.exchange.expire_exchange(exchange.id)
                await notify_expire_offer(bot, stp_repo, exchange)


async def notify_expire_offer(bot: Bot, stp_repo: MainRequestsRepo, exchange: Exchange):
    shift_date = exchange.shift_date.strftime("%d.%m.%Y")
    shift_time = f"{exchange.shift_start_time}-{exchange.shift_end_time}"

    seller = await stp_repo.employee.get_users(user_id=exchange.seller_id)
    seller_name = format_fullname(
        seller.fullname,
        short=True,
        gender_emoji=True,
        username=seller.username,
        user_id=seller.user_id,
    )

    if exchange.payment_type == "immediate":
        payment_info = "Сразу при покупке"
    elif exchange.payment_date:
        payment_info = f"До {exchange.payment_date.strftime('%d.%m.%Y')}"
    else:
        payment_info = "По договоренности"

    deeplink = await create_start_link(
        bot=bot, payload=f"exchange_{exchange.id}", encode=True
    )

    await bot.send_message(
        chat_id=exchange.seller_id,
        text=f"""⏳ <b>Предложение стекло</b>

У предложения наступило время начала

<blockquote>📅 <b>Предложение:</b> {shift_date} {shift_time} ПРМ
💰 <b>Цена:</b> {exchange.price} р.

👤 <b>Продавец:</b> {seller_name}
💳 <b>Оплата:</b> {payment_info}</blockquote>

<i>Ты можешь отредактировать его и опубликовать снова</i>""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Открыть сделку", url=deeplink)]
            ]
        ),
    )

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
    # Приводим время к локальной временной зоне если оно timezone-naive
    start_time = exchange.start_time
    if start_time.tzinfo is None:
        start_time = tz.localize(start_time)

    shift_date = start_time.strftime("%d.%m.%Y")
    start_time_str = start_time.strftime("%H:%M")

    if exchange.end_time:
        end_time = exchange.end_time
        if end_time.tzinfo is None:
            end_time = tz.localize(end_time)
        end_time_str = end_time.strftime("%H:%M")
    else:
        end_time_str = "??:??"

    shift_time = f"{start_time_str}-{end_time_str}"

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

    price_per_hour = 0
    if exchange.start_time and exchange.end_time:
        try:
            # Рассчитываем продолжительность из TIMESTAMP полей
            duration = exchange.end_time - exchange.start_time
            shift_hours = duration.total_seconds() / 3600  # Переводим в часы

            # Рассчитываем цену за час
            if shift_hours > 0 and exchange.price:
                price_per_hour = round(exchange.price / shift_hours, 2)
        except (ValueError, AttributeError):
            # Если не удалось рассчитать, оставляем значения по умолчанию
            shift_hours = 0
            price_per_hour = 0

    deeplink = await create_start_link(
        bot=bot, payload=f"exchange_{exchange.id}", encode=True
    )

    await bot.send_message(
        chat_id=exchange.seller_id,
        text=f"""⏳ <b>Предложение истекло</b>

У предложения наступило время {"начала" if exchange.type == "sell" else "конца"}

<blockquote>📅 <b>Предложение:</b> <code>{shift_time} {shift_date} ПРМ</code>
💰 <b>Цена:</b> <code>{exchange.price} р. ({price_per_hour} р./час)</code>

👤 <b>Продавец:</b> {seller_name}
💳 <b>Оплата:</b> {payment_info}</blockquote>

<i>Ты можешь отредактировать его и опубликовать снова</i>""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Открыть сделку", url=deeplink)]
            ]
        ),
    )

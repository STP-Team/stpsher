"""Exchanges (shift marketplace) scheduler."""

import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.deep_linking import create_start_link
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from stp_database.models.STP import Exchange
from stp_database.repo.STP import MainRequestsRepo

from tgbot.dialogs.getters.common.exchanges.exchanges import get_exchange_text
from tgbot.misc.helpers import tz_perm
from tgbot.services.broadcaster import send_message
from tgbot.services.schedulers.base import BaseScheduler

logger = logging.getLogger(__name__)

TIME_WINDOW = timedelta(minutes=5)
MIN_RESCHEDULE = timedelta(minutes=30)

MSG = {
    "expired": "⏳ <b>Сделка истекла</b>\n\nУ сделки наступило время {time_type}\n\n{info}\n\n<i>Ты можешь отредактировать ее и опубликовать снова</i>",
    "subscription_match": "🔔 <b>Новая сделка</b>\n\nНайдена сделка, соответствующая подписке <b>{subscription_name}</b>:\n\n{exchange_info}",
    "upcoming_seller": "{emoji} <b>Напоминание о смене</b>\n\nПроданный промежуток смены начинается {time}\n\n{info}",
    "upcoming_buyer": "{emoji} <b>Напоминание о смене</b>\n\nСмена, которую ты купил, начинается {time}\n\n{info}",
    "payment_buyer": "💰 <b>Время оплаты</b>\n\nНаступила дата оплаты для купленной смены\n\n{info}\n\n<i>Пожалуйста, проверь получение оплаты и отметь это в сделке</i>",
    "payment_seller": "📅 <b>Дата оплаты наступила</b>\n\nДля проданной смены наступила дата оплаты\n\n{info}\n\n<i>Пожалуйста, произведи оплату покупателю</i>",
    "reminder_buyer": "🕐 <b>Ежедневное напоминание</b>\n\nУ тебя есть неоплаченные купленные сделки:\n\n{list}\n\n<i>Пожалуйста, проверь получение оплаты</i>",
    "reminder_seller": "🕐 <b>Ежедневное напоминание</b>\n\nУ тебя есть неоплаченные проданные сделки:\n\n{list}\n\n<i>Пожалуйста, произведи оплату покупателям</i>",
}

# Export aliases for backward compatibility
MESSAGES = MSG


async def create_exchange_deeplink(bot: Bot, exchange_id: int) -> str:
    """Create exchange deeplink."""
    return await create_start_link(bot, f"exchange_{exchange_id}", encode=True)


async def create_subscription_deeplink(bot: Bot, subscription_id: int) -> str:
    """Create subscription deeplink."""
    return await create_start_link(bot, f"subscription_{subscription_id}", encode=True)


def create_subscription_keyboard(
    exchange_deeplink: str, subscription_deeplink: str
) -> InlineKeyboardMarkup:
    """Create subscription notification keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎭 Открыть сделку", url=exchange_deeplink)],
            [
                InlineKeyboardButton(
                    text="🔔 Настроить подписку", url=subscription_deeplink
                )
            ],
        ]
    )


class ExchangesScheduler(BaseScheduler):
    """Exchanges marketplace scheduler."""

    def __init__(self):
        super().__init__("Биржа подмен")

    def setup_jobs(
        self,
        scheduler: AsyncIOScheduler,
        stp_session_pool: async_sessionmaker[AsyncSession],
        bot: Bot,
    ):
        jobs = [
            (
                "interval",
                1,
                self._expired_job,
                "exchanges_expired",
                "Проверка истекших",
            ),
            (
                "interval",
                10,
                self._upcoming_1h_job,
                "exchanges_upcoming_1h",
                "Уведомления за 1 час",
            ),
            (
                "interval",
                60,
                self._upcoming_1d_job,
                "exchanges_upcoming_1d",
                "Уведомления за 1 день",
            ),
            (
                "cron",
                None,
                self._payment_job,
                "exchanges_payment",
                "Уведомления об оплате",
            ),
            (
                "cron",
                None,
                self._reminder_job,
                "exchanges_reminder",
                "Напоминания об оплате",
            ),
        ]

        for trigger, interval, func, jid, name in jobs:
            kwargs = {
                "func": func,
                "args": [stp_session_pool, bot],
                "id": jid,
                "name": name,
                "coalesce": True,
                "misfire_grace_time": 300,
                "replace_existing": True,
            }
            if trigger == "interval":
                kwargs.update({"trigger": "interval", "minutes": interval})
            else:
                kwargs.update({
                    "trigger": "cron",
                    "hour": 12,
                    "minute": 0,
                    "timezone": tz_perm,
                })
            scheduler.add_job(**kwargs)

    async def _expired_job(self, pool, bot):
        await check_expired_offers(pool, bot)

    async def _upcoming_1h_job(self, pool, bot):
        await check_upcoming(pool, bot, 1)

    async def _upcoming_1d_job(self, pool, bot):
        await check_upcoming(pool, bot, 24)

    async def _payment_job(self, pool, bot):
        await check_payment_dates(pool, bot)

    async def _reminder_job(self, pool, bot):
        await check_payment_reminders(pool, bot)


async def check_expired_offers(
    stp_session_pool: async_sessionmaker[AsyncSession], bot: Bot
):
    """Check and hide expired offers."""
    async with stp_session_pool() as session:
        repo = MainRequestsRepo(session)
        exchanges = await repo.exchange.get_active_exchanges(
            include_private=True, limit=200
        )
        now = datetime.now(tz_perm)

        for exc in exchanges:
            try:
                exp_time = (
                    exc.start_time if exc.owner_intent == "sell" else exc.end_time
                )
                if not exp_time:
                    continue

                exp_time = _to_local(exp_time)
                if now >= exp_time:
                    await repo.exchange.expire_exchange(exc.id)
                    await _notify_expired(bot, repo, exc)
            except Exception as e:
                logger.error(f"[Exchanges] Expired error {exc.id}: {e}")


async def _notify_expired(bot: Bot, repo: MainRequestsRepo, exc: Exchange):
    if not exc.owner_id:
        return

    owner = await repo.employee.get_users(user_id=exc.owner_id)
    if not owner:
        return

    info = await get_exchange_text(repo, exc, user_id=owner.user_id)
    link = await create_start_link(bot, f"exchange_{exc.id}", encode=True)
    msg = MSG["expired"].format(
        time_type="начала" if exc.owner_intent == "sell" else "конца", info=info
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🎭 Открыть сделку", url=link)]]
    )
    if exc.owner_intent == "sell" and _can_reschedule(exc):
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text="⏰ Перенести автоматически", callback_data=f"reschedule_{exc.id}"
            )
        ])

    await send_message(bot, exc.owner_id, msg, reply_markup=kb)


async def check_upcoming(
    stp_session_pool: async_sessionmaker[AsyncSession], bot: Bot, hours: int
):
    """Check upcoming exchanges and notify."""
    async with stp_session_pool() as session:
        repo = MainRequestsRepo(session)
        now = datetime.now(tz_perm)
        target = now + timedelta(hours=hours)
        start, end = target - TIME_WINDOW, target + TIME_WINDOW

        exchanges = await repo.exchange.get_upcoming_sold_exchanges(
            start_after=start, start_before=end, limit=500
        )

        for exc in exchanges:
            try:
                await _notify_upcoming(bot, repo, exc, hours)
            except Exception as e:
                logger.error(f"[Exchanges] Upcoming error {exc.id}: {e}")


async def _notify_upcoming(bot: Bot, repo: MainRequestsRepo, exc: Exchange, hours: int):
    link = await create_start_link(bot, f"exchange_{exc.id}", encode=True)
    emoji, time_text = ("⏰", "через 1 час") if hours == 1 else ("📅", "завтра")
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🎭 Открыть сделку", url=link)]]
    )

    seller_id = exc.owner_id if exc.owner_intent == "sell" else exc.counterpart_id
    buyer_id = exc.counterpart_id if exc.owner_intent == "sell" else exc.owner_id

    if seller_id:
        info = await get_exchange_text(repo, exc, user_id=seller_id)
        await send_message(
            bot,
            seller_id,
            MSG["upcoming_seller"].format(emoji=emoji, time=time_text, info=info),
            reply_markup=kb,
        )

    if buyer_id:
        info = await get_exchange_text(repo, exc, user_id=buyer_id)
        await send_message(
            bot,
            buyer_id,
            MSG["upcoming_buyer"].format(emoji=emoji, time=time_text, info=info),
            reply_markup=kb,
        )


async def check_payment_dates(
    stp_session_pool: async_sessionmaker[AsyncSession], bot: Bot
):
    """Check payment date notifications."""
    async with stp_session_pool() as session:
        repo = MainRequestsRepo(session)
        today = datetime.now(tz_perm).date()
        exchanges = await repo.exchange.get_exchanges_by_payment_date(
            payment_date=today, status="sold", is_paid=False
        )

        for exc in exchanges:
            await _notify_payment(bot, repo, exc)


async def _notify_payment(bot: Bot, repo: MainRequestsRepo, exc: Exchange):
    link = await create_start_link(bot, f"exchange_{exc.id}", encode=True)
    seller_id = exc.owner_id if exc.owner_intent == "sell" else exc.counterpart_id
    buyer_id = exc.counterpart_id if exc.owner_intent == "sell" else exc.owner_id

    if buyer_id:
        info = await get_exchange_text(repo, exc, user_id=buyer_id)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💰 Отметить оплату", url=link)]
            ]
        )
        await send_message(
            bot, buyer_id, MSG["payment_buyer"].format(info=info), reply_markup=kb
        )

    if seller_id:
        info = await get_exchange_text(repo, exc, user_id=seller_id)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🎭 Открыть сделку", url=link)]]
        )
        await send_message(
            bot, seller_id, MSG["payment_seller"].format(info=info), reply_markup=kb
        )


async def check_payment_reminders(
    stp_session_pool: async_sessionmaker[AsyncSession], bot: Bot
):
    """Daily payment reminders."""
    async with stp_session_pool() as session:
        repo = MainRequestsRepo(session)
        users_data = await repo.exchange.get_users_with_unpaid_exchanges(
            status="sold", is_paid=False
        )

        for data in users_data:
            await _send_reminder(bot, repo, data)


async def _send_reminder(bot: Bot, repo: MainRequestsRepo, data: dict):
    user_id, exchanges = data["user_id"], data["exchanges"]
    if not exchanges:
        return

    today = datetime.now(tz_perm).date()
    buyer, seller = [], []

    for exc in exchanges:
        if exc.payment_type == "on_date" and exc.payment_date:
            if _to_local(exc.payment_date).date() > today:
                continue

        if exc.owner_intent == "sell":
            if exc.counterpart_id == user_id:
                buyer.append(exc)
            elif exc.owner_id == user_id:
                seller.append(exc)
        else:
            if exc.owner_id == user_id:
                buyer.append(exc)
            elif exc.counterpart_id == user_id:
                seller.append(exc)

    if buyer:
        infos = [f"• {await get_exchange_text(repo, exc, user_id)}" for exc in buyer]
        await send_message(
            bot, user_id, MSG["reminder_buyer"].format(list="\n\n".join(infos))
        )

    if seller:
        infos = [f"• {await get_exchange_text(repo, exc, user_id)}" for exc in seller]
        await send_message(
            bot, user_id, MSG["reminder_seller"].format(list="\n\n".join(infos))
        )


def _to_local(dt: datetime) -> datetime:
    return tz_perm.localize(dt) if dt.tzinfo is None else dt


def _can_reschedule(exc: Exchange) -> bool:
    if not exc.end_time:
        return False

    now = datetime.now(tz_perm)
    end = _to_local(exc.end_time)

    if end.date() != now.date() or end <= now:
        return False

    next_slot = (
        now.replace(minute=30, second=0, microsecond=0)
        if now.minute < 30
        else (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    )
    return end - next_slot >= MIN_RESCHEDULE

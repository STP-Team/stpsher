import logging
from datetime import datetime, timedelta
from typing import Tuple

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.deep_linking import create_start_link
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from stp_database import Exchange, MainRequestsRepo

from tgbot.dialogs.getters.common.exchanges.exchanges import (
    get_exchange_text,
)
from tgbot.misc.helpers import tz
from tgbot.services.broadcaster import send_message
from tgbot.services.schedulers.base import BaseScheduler

logger = logging.getLogger(__name__)

# Scheduler Configuration Constants
SCHEDULER_CONFIG = {
    "expired_offers": {
        "interval_minutes": 1,
        "misfire_grace_time": 300,
        "id": "exchanges_check_expired_offers",
        "name": "Проверка истекших предложений",
    },
    "subscription_matches": {
        "interval_minutes": 2,
        "misfire_grace_time": 300,
        "id": "exchanges_check_subscription_matches",
        "name": "Проверка совпадений подписок",
    },
    "upcoming_1hour": {
        "interval_minutes": 10,
        "misfire_grace_time": 300,
        "id": "exchanges_notify_1hour",
        "name": "Уведомления за 1 час до обмена",
    },
    "upcoming_1day": {
        "interval_hours": 1,
        "misfire_grace_time": 600,
        "id": "exchanges_notify_1day",
        "name": "Уведомления за 1 день до обмена",
    },
    "payment_notifications": {
        "interval_hours": 6,
        "misfire_grace_time": 600,
        "id": "exchanges_payment_date_notifications",
        "name": "Уведомления о датах оплаты",
    },
    "immediate_reminders": {
        "interval_hours": 12,
        "misfire_grace_time": 600,
        "id": "exchanges_immediate_payment_reminders",
        "name": "Напоминания об immediate оплате",
    },
    "daily_payment_reminder": {
        "trigger": "cron",
        "hour": 12,
        "minute": 0,
        "misfire_grace_time": 1800,  # 30 minutes
        "id": "exchanges_daily_payment_reminder",
        "name": "Ежедневное напоминание об оплате в 12:00",
    },
}

# Notification Messages Templates
MESSAGES = {
    "expired_offer": """⏳ <b>Сделка истекла</b>

У сделки наступило время {time_type}

{exchange_info}

<i>Ты можешь отредактировать ее и опубликовать снова</i>""",
    "subscription_match": """🔔 <b>Новая сделка</b>

Найдена сделка, соответствующая подписке <b>{subscription_name}</b>:

{exchange_info}""",
    "upcoming_seller": """{emoji} <b>Напоминание о смене</b>

Проданный промежуток смены начинается {time_text}

{exchange_info}""",
    "upcoming_buyer": """{emoji} <b>Напоминание о смене</b>

Смена, которую ты купил, начинается {time_text}

{exchange_info}""",
    "payment_date_buyer": """💰 <b>Время оплаты</b>

Наступила дата оплаты для купленной смены

{exchange_info}

<i>Пожалуйста, произведи оплату и отметь это в сделке</i>""",
    "payment_date_seller": """📅 <b>Дата оплаты наступила</b>

Для проданной смены наступила дата оплаты

{exchange_info}

<i>Покупатель должен произвести оплату</i>""",
    "immediate_reminder": """⚡ <b>Напоминание об оплате</b>

Ты еще не отметил оплату для купленной смены с моментальной оплатой

{exchange_info}

<i>Пожалуйста, произведи оплату и отметь это в сделке</i>""",
    "daily_payment_reminder": """🕐 <b>Ежедневное напоминание об оплате</b>

У тебя есть неоплаченные обмены:

{exchanges_info}

<i>Пожалуйста, произведи оплату и отметь это в соответствующих сделках</i>""",
}

# Button Text Constants
BUTTONS = {
    "open_exchange": "🎭 Открыть сделку",
    "reschedule_auto": "⏰ Перенести автоматически",
    "mark_payment": "💰 Отметить оплату",
    "configure_subscription": "🔔 Настроить подписку",
}

# Time-related Constants
TIME_CONSTANTS = {
    "subscription_check_window_seconds": 300,  # 5 minutes
    "upcoming_notification_window_minutes": 5,
    "minimum_reschedule_minutes": 30,
}


# Helper Functions
async def create_exchange_deeplink(bot: Bot, exchange_id: int) -> str:
    """Создает deeplink для обмена.

    Args:
        bot: Экземпляр бота
        exchange_id: ID обмена

    Returns:
        Deeplink для обмена
    """
    return await create_start_link(
        bot=bot, payload=f"exchange_{exchange_id}", encode=True
    )


async def create_subscription_deeplink(bot: Bot, subscription_id: int) -> str:
    """Создает deeplink для подписки.

    Args:
        bot: Экземпляр бота
        subscription_id: ID подписки

    Returns:
        Deeplink для подписки
    """
    return await create_start_link(
        bot=bot, payload=f"subscription_{subscription_id}", encode=True
    )


def create_basic_keyboard(
    deeplink: str, button_text: str = None
) -> InlineKeyboardMarkup:
    """Создает базовую клавиатуру с одной кнопкой.

    Args:
        deeplink: Ссылка для кнопки
        button_text: Текст кнопки (по умолчанию "Открыть сделку")

    Returns:
        Объект клавиатуры
    """
    if button_text is None:
        button_text = BUTTONS["open_exchange"]

    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=button_text, url=deeplink)]]
    )


def create_payment_keyboard(deeplink: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру для оплаты.

    Args:
        deeplink: Ссылка для кнопки

    Returns:
        Объект клавиатуры
    """
    return create_basic_keyboard(deeplink, BUTTONS["mark_payment"])


def create_subscription_keyboard(
    exchange_deeplink: str, subscription_deeplink: str
) -> InlineKeyboardMarkup:
    """Создает клавиатуру для уведомлений подписки.

    Args:
        exchange_deeplink: Ссылка на обмен
        subscription_deeplink: Ссылка на подписку

    Returns:
        Объект клавиатуры
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BUTTONS["open_exchange"], url=exchange_deeplink
                )
            ],
            [
                InlineKeyboardButton(
                    text=BUTTONS["configure_subscription"], url=subscription_deeplink
                )
            ],
        ]
    )


def create_expire_keyboard(deeplink: str, exchange: Exchange) -> InlineKeyboardMarkup:
    """Создает клавиатуру для истекших сделок.

    Args:
        deeplink: Ссылка на обмен
        exchange: Объект обмена

    Returns:
        Объект клавиатуры
    """
    inline_keyboard = [
        [InlineKeyboardButton(text=BUTTONS["open_exchange"], url=deeplink)]
    ]

    # Для продаж добавляем кнопку автоматического переноса (если возможно)
    if exchange.type == "sell" and can_reschedule_exchange(exchange):
        inline_keyboard.append([
            InlineKeyboardButton(
                text=BUTTONS["reschedule_auto"],
                callback_data=f"reschedule_{exchange.id}",
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_time_text_and_emoji(hours_before: int) -> Tuple[str, str]:
    """Получает текст времени и эмодзи для уведомлений.

    Args:
        hours_before: За сколько часов до события

    Returns:
        Кортеж (время_текст, эмодзи)
    """
    if hours_before == 1:
        return "через 1 час", "⏰"
    elif hours_before == 24:
        return "завтра", "📅"
    else:
        return f"через {hours_before} часов", "⏰"


def normalize_timezone(dt: datetime) -> datetime:
    """Приводит datetime к локальной временной зоне.

    Args:
        dt: Объект datetime

    Returns:
        datetime в локальной временной зоне
    """
    if dt.tzinfo is None:
        return tz.localize(dt)
    return dt


def can_reschedule_exchange(exchange: Exchange) -> bool:
    """Проверяет, можно ли автоматически перенести сделку.

    Args:
        exchange: Экземпляр сделки

    Returns:
        bool: True если сделка может быть перенесена автоматически
    """
    if not exchange.end_time:
        return False

    # Получаем текущее время в локальной зоне
    current_local_time = datetime.now(tz)

    # Проверяем, что сделка сегодня
    today = current_local_time.date()

    # Убеждаемся, что end_time timezone-aware для сравнения
    end_time = normalize_timezone(exchange.end_time)

    # Проверяем, что конец сделки сегодня
    if end_time.date() != today:
        return False

    # Проверяем, что конец сделки еще не прошел
    if end_time <= current_local_time:
        return False

    # Вычисляем следующий доступный получасовой интервал
    current_time = current_local_time.time()
    if current_time.minute < 30:
        next_slot_start = current_local_time.replace(minute=30, second=0, microsecond=0)
    else:
        next_slot_start = current_local_time.replace(
            minute=0, second=0, microsecond=0
        ) + timedelta(hours=1)

    # Проверяем, что от следующего слота до конца сделки минимум указанное время
    time_remaining = end_time - next_slot_start
    return time_remaining >= timedelta(
        minutes=TIME_CONSTANTS["minimum_reschedule_minutes"]
    )


class ExchangesScheduler(BaseScheduler):
    """Планировщик биржи подмен."""

    def __init__(self):
        super().__init__("Биржа подмен")

    def setup_jobs(
        self, scheduler: AsyncIOScheduler, session_pool, bot: Bot, kpi_session_pool=None
    ):
        """Настройка всех задач биржи."""
        self.logger.info("Настройка задач биржи...")

        # Конфигурация задач с их функциями
        job_configs = [
            ("expired_offers", self._check_expired_offers),
            ("subscription_matches", self._check_subscription_matches),
            ("upcoming_1hour", self._check_upcoming_exchanges_1hour),
            ("upcoming_1day", self._check_upcoming_exchanges_1day),
            ("payment_notifications", self._check_payment_date_notifications),
            ("immediate_reminders", self._check_immediate_payment_reminders),
            ("daily_payment_reminder", self._check_daily_payment_reminders),
        ]

        for config_key, func in job_configs:
            config = SCHEDULER_CONFIG[config_key]
            job_kwargs = {
                "func": func,
                "args": [session_pool, bot],
                "id": config["id"],
                "name": config["name"],
                "coalesce": True,
                "misfire_grace_time": config["misfire_grace_time"],
                "replace_existing": True,
            }

            # Настраиваем триггер в зависимости от типа
            if config.get("trigger") == "cron":
                job_kwargs["trigger"] = "cron"
                job_kwargs["hour"] = config["hour"]
                job_kwargs["minute"] = config["minute"]
                job_kwargs["timezone"] = tz  # Используем локальную временную зону
            else:
                job_kwargs["trigger"] = "interval"
                # Добавляем интервал в зависимости от конфигурации
                if "interval_minutes" in config:
                    job_kwargs["minutes"] = config["interval_minutes"]
                elif "interval_hours" in config:
                    job_kwargs["hours"] = config["interval_hours"]

            scheduler.add_job(**job_kwargs)

    async def _check_expired_offers(self, session_pool, bot: Bot) -> None:
        """Проверка истекших сделок.

        Args:
            session_pool: Сессия с БД
            bot: Экземпляр бота
        """
        await check_expired_offers(session_pool, bot)

    async def _check_subscription_matches(self, session_pool, bot: Bot) -> None:
        """Проверка совпадений подписок с новыми обменами.

        Args:
            session_pool: Сессия с БД
            bot: Экземпляр бота
        """
        await check_subscription_matches(session_pool, bot)

    async def _check_upcoming_exchanges_1hour(self, session_pool, bot: Bot) -> None:
        """Проверка обменов, начинающихся через 1 час.

        Args:
            session_pool: Сессия с БД
            bot: Экземпляр бота
        """
        await check_upcoming_exchanges(session_pool, bot, hours_before=1)

    async def _check_upcoming_exchanges_1day(self, session_pool, bot: Bot) -> None:
        """Проверка обменов, начинающихся через 1 день.

        Args:
            session_pool: Сессия с БД
            bot: Экземпляр бота
        """
        await check_upcoming_exchanges(session_pool, bot, hours_before=24)

    async def _check_payment_date_notifications(self, session_pool, bot: Bot) -> None:
        """Проверка наступивших дат оплаты.

        Args:
            session_pool: Сессия с БД
            bot: Экземпляр бота
        """
        await check_payment_date_notifications(session_pool, bot)

    async def _check_immediate_payment_reminders(self, session_pool, bot: Bot) -> None:
        """Проверка напоминаний об immediate оплате.

        Args:
            session_pool: Сессия с БД
            bot: Экземпляр бота
        """
        await check_immediate_payment_reminders(session_pool, bot)

    async def _check_daily_payment_reminders(self, session_pool, bot: Bot) -> None:
        """Ежедневная проверка неоплаченных обменов в 12:00.

        Args:
            session_pool: Сессия с БД
            bot: Экземпляр бота
        """
        await check_daily_payment_reminders(session_pool, bot)


async def check_expired_offers(session_pool, bot: Bot) -> None:
    """Проверка и скрытие истекших сделок.

    Args:
        session_pool: Пул сессий основной БД
        bot: Экземпляр бота
    """
    try:
        async with session_pool() as stp_session:
            stp_repo = MainRequestsRepo(stp_session)

            active_exchanges = await stp_repo.exchange.get_active_exchanges(
                include_private=True, limit=200
            )

            if not active_exchanges:
                return

            current_local_time = datetime.now(tz)
            expired_count = 0

            for exchange in active_exchanges:
                try:
                    # Определяем время истечения в зависимости от типа предложения
                    if exchange.type == "sell":
                        expiration_datetime = exchange.start_time
                    elif exchange.type == "buy":
                        expiration_datetime = exchange.end_time
                    else:
                        continue

                    # Если время истечения не задано, пропускаем
                    if expiration_datetime is None:
                        continue

                    # Приводим время истечения к локальной временной зоне
                    expiration_datetime = normalize_timezone(expiration_datetime)

                    # Проверяем истечение предложения
                    if current_local_time >= expiration_datetime:
                        await stp_repo.exchange.expire_exchange(exchange.id)
                        await notify_expire_offer(bot, stp_repo, exchange)
                        expired_count += 1

                except Exception as e:
                    logger.error(f"Ошибка обработки истекшей сделки {exchange.id}: {e}")

            if expired_count > 0:
                logger.info(f"Обработано {expired_count} истекших сделок")

    except Exception as e:
        logger.error(f"Ошибка проверки истекших предложений: {e}")


async def notify_expire_offer(
    bot: Bot, stp_repo: MainRequestsRepo, exchange: Exchange
) -> None:
    """Уведомление об истекшей по времени сделке.

    Args:
        bot: Экземпляр бота
        stp_repo: Репозиторий операций с базой STP
        exchange: Экземпляр сделки с моделью Exchange
    """
    try:
        # Определяем владельца сделки
        owner_id = exchange.seller_id if exchange.type == "sell" else exchange.buyer_id
        if not owner_id:
            logger.warning(f"Не найден владелец для сделки {exchange.id}")
            return

        owner = await stp_repo.employee.get_users(user_id=owner_id)
        if not owner:
            logger.warning(
                f"Не найден пользователь {owner_id} для сделки {exchange.id}"
            )
            return

        # Получаем информацию об обмене и создаем deeplink
        exchange_info = await get_exchange_text(
            stp_repo, exchange, user_id=owner.user_id
        )
        deeplink = await create_exchange_deeplink(bot, exchange.id)

        # Формируем сообщение
        time_type = "начала" if exchange.type == "sell" else "конца"
        message_text = MESSAGES["expired_offer"].format(
            time_type=time_type, exchange_info=exchange_info
        )

        # Создаем клавиатуру
        reply_markup = create_expire_keyboard(deeplink, exchange)

        # Отправляем уведомление
        success = await send_message(
            bot=bot, user_id=owner_id, text=message_text, reply_markup=reply_markup
        )

        if success:
            logger.info(f"Отправлено уведомление об истекшей сделке {exchange.id}")

    except Exception as e:
        logger.error(
            f"Ошибка отправки уведомления об истекшей сделке {exchange.id}: {e}"
        )


async def check_subscription_matches(session_pool, bot: Bot) -> None:
    """Проверка новых обменов на совпадения с подписками.

    Args:
        session_pool: Пул сессий основной БД
        bot: Экземпляр бота
    """
    try:
        async with session_pool() as stp_session:
            stp_repo = MainRequestsRepo(stp_session)

            # Получаем новые обмены (созданные за последние несколько минут)
            current_time = datetime.now(tz)
            cutoff_time = current_time - timedelta(
                seconds=TIME_CONSTANTS["subscription_check_window_seconds"]
            )

            # Оптимизация: получаем только обмены, созданные после cutoff_time
            recent_exchanges = await stp_repo.exchange.get_recent_exchanges(
                created_after=cutoff_time, include_private=False, limit=50
            )

            if not recent_exchanges:
                return

            matches_found = 0

            for exchange in recent_exchanges:
                try:
                    # Находим все подписки, соответствующие этому обмену
                    matching_subscriptions = (
                        await stp_repo.exchange.find_matching_subscriptions(exchange)
                    )

                    for subscription in matching_subscriptions:
                        await notify_subscription_match(
                            bot, stp_repo, subscription, exchange
                        )
                        matches_found += 1

                except Exception as e:
                    logger.error(
                        f"Ошибка обработки совпадений для обмена {exchange.id}: {e}"
                    )

            if matches_found > 0:
                logger.info(f"Найдено и обработано {matches_found} совпадений подписок")

    except Exception as e:
        logger.error(f"Ошибка проверки совпадений подписок: {e}")


async def notify_subscription_match(
    bot: Bot, stp_repo: MainRequestsRepo, subscription, exchange: Exchange
) -> None:
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
            logger.warning(
                f"Не найден пользователь {subscription.subscriber_id} для подписки {subscription.id}"
            )
            return

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

    except Exception as e:
        logger.error(
            f"Ошибка отправки уведомления о совпадении подписки {subscription.id}: {e}"
        )


async def check_upcoming_exchanges(session_pool, bot: Bot, hours_before: int) -> None:
    """Проверка и отправка уведомлений о приближающихся обменах.

    Args:
        session_pool: Пул сессий основной БД
        bot: Экземпляр бота
        hours_before: За сколько часов до начала отправлять уведомление
    """
    try:
        async with session_pool() as stp_session:
            stp_repo = MainRequestsRepo(stp_session)

            current_local_time = datetime.now(tz)
            target_time = current_local_time + timedelta(hours=hours_before)

            # Определяем временное окно для уведомлений
            time_window = timedelta(
                minutes=TIME_CONSTANTS["upcoming_notification_window_minutes"]
            )
            target_start = target_time - time_window
            target_end = target_time + time_window

            # Получаем проданные обмены, которые еще не начались
            upcoming_exchanges = await stp_repo.exchange.get_upcoming_sold_exchanges(
                start_after=target_start, start_before=target_end, limit=500
            )

            if not upcoming_exchanges:
                return

            notifications_sent = 0

            for exchange in upcoming_exchanges:
                try:
                    # Отправляем уведомления обеим сторонам
                    await notify_upcoming_exchange(
                        bot, stp_repo, exchange, hours_before
                    )
                    notifications_sent += 1

                except Exception as e:
                    logger.error(
                        f"Ошибка отправки уведомления для обмена {exchange.id}: {e}"
                    )

            if notifications_sent > 0:
                logger.info(
                    f"Отправлено уведомлений о приближающихся обменах ({hours_before}ч): {notifications_sent}"
                )

    except Exception as e:
        logger.error(f"Ошибка проверки приближающихся обменов ({hours_before}ч): {e}")


async def notify_upcoming_exchange(
    bot: Bot, stp_repo: MainRequestsRepo, exchange: Exchange, hours_before: int
) -> None:
    """Отправка уведомления о приближающемся обмене.

    Args:
        bot: Экземпляр бота
        stp_repo: Репозиторий операций с базой STP
        exchange: Экземпляр сделки
        hours_before: За сколько часов отправляется уведомление
    """
    try:
        # Создаем deeplink и получаем текст времени
        deeplink = await create_exchange_deeplink(bot, exchange.id)
        time_text, emoji = get_time_text_and_emoji(hours_before)
        reply_markup = create_basic_keyboard(deeplink)

        notifications_sent = 0

        # Уведомление продавцу
        if exchange.seller_id:
            seller_exchange_info = await get_exchange_text(
                stp_repo, exchange, user_id=exchange.seller_id
            )

            seller_message = MESSAGES["upcoming_seller"].format(
                emoji=emoji, time_text=time_text, exchange_info=seller_exchange_info
            )

            success = await send_message(
                bot=bot,
                user_id=exchange.seller_id,
                text=seller_message,
                reply_markup=reply_markup,
            )
            if success:
                notifications_sent += 1

        # Уведомление покупателю
        if exchange.buyer_id:
            buyer_exchange_info = await get_exchange_text(
                stp_repo, exchange, user_id=exchange.buyer_id
            )

            buyer_message = MESSAGES["upcoming_buyer"].format(
                emoji=emoji, time_text=time_text, exchange_info=buyer_exchange_info
            )

            success = await send_message(
                bot=bot,
                user_id=exchange.buyer_id,
                text=buyer_message,
                reply_markup=reply_markup,
            )
            if success:
                notifications_sent += 1

        if notifications_sent > 0:
            logger.info(
                f"Отправлено {notifications_sent} уведомлений о приближающемся обмене {exchange.id} "
                f"(за {hours_before}ч)"
            )

    except Exception as e:
        logger.error(
            f"Ошибка отправки уведомления о приближающемся обмене {exchange.id}: {e}"
        )


async def check_payment_date_notifications(session_pool, bot: Bot) -> None:
    """Проверка и отправка уведомлений о наступивших датах оплаты.

    Args:
        session_pool: Пул сессий основной БД
        bot: Экземпляр бота
    """
    try:
        async with session_pool() as stp_session:
            stp_repo = MainRequestsRepo(stp_session)

            current_local_time = datetime.now(tz)
            today = current_local_time.date()

            # Получаем проданные неоплаченные обмены с наступившей датой оплаты
            exchanges_to_notify = await stp_repo.exchange.get_exchanges_by_payment_date(
                payment_date=today, status="sold", is_paid=False
            )

            if not exchanges_to_notify:
                return

            notifications_sent = 0

            for exchange in exchanges_to_notify:
                try:
                    await notify_payment_date_reached(bot, stp_repo, exchange)
                    notifications_sent += 1
                except Exception as e:
                    logger.error(
                        f"Ошибка отправки уведомления об оплате для обмена {exchange.id}: {e}"
                    )

            if notifications_sent > 0:
                logger.info(
                    f"Отправлено {notifications_sent} уведомлений о наступивших датах оплаты"
                )

    except Exception as e:
        logger.error(f"Ошибка проверки уведомлений о датах оплаты: {e}")


async def check_immediate_payment_reminders(session_pool, bot: Bot) -> None:
    """Проверка и отправка ежедневных напоминаний об immediate оплате.

    Args:
        session_pool: Пул сессий основной БД
        bot: Экземпляр бота
    """
    try:
        async with session_pool() as stp_session:
            stp_repo = MainRequestsRepo(stp_session)

            # Получаем проданные неоплаченные обмены с immediate оплатой
            exchanges_to_remind = (
                await stp_repo.exchange.get_immediate_unpaid_exchanges(
                    status="sold", is_paid=False, payment_type="immediate"
                )
            )

            if not exchanges_to_remind:
                return

            reminders_sent = 0

            for exchange in exchanges_to_remind:
                try:
                    await notify_immediate_payment_reminder(bot, stp_repo, exchange)
                    reminders_sent += 1
                except Exception as e:
                    logger.error(
                        f"Ошибка отправки напоминания об оплате для обмена {exchange.id}: {e}"
                    )

            if reminders_sent > 0:
                logger.info(
                    f"Отправлено {reminders_sent} напоминаний об immediate оплате"
                )

    except Exception as e:
        logger.error(f"Ошибка проверки напоминаний об immediate оплате: {e}")


async def notify_payment_date_reached(
    bot: Bot, stp_repo: MainRequestsRepo, exchange: Exchange
) -> None:
    """Отправка уведомления о наступившей дате оплаты.

    Args:
        bot: Экземпляр бота
        stp_repo: Репозиторий операций с базой STP
        exchange: Экземпляр сделки
    """
    try:
        deeplink = await create_exchange_deeplink(bot, exchange.id)
        notifications_sent = 0

        # Уведомляем покупателя о необходимости оплаты
        if exchange.buyer_id:
            buyer_exchange_info = await get_exchange_text(
                stp_repo, exchange, user_id=exchange.buyer_id
            )

            buyer_message = MESSAGES["payment_date_buyer"].format(
                exchange_info=buyer_exchange_info
            )

            success = await send_message(
                bot=bot,
                user_id=exchange.buyer_id,
                text=buyer_message,
                reply_markup=create_payment_keyboard(deeplink),
            )
            if success:
                notifications_sent += 1

        # Уведомляем продавца о том, что покупатель должен произвести оплату
        if exchange.seller_id:
            seller_exchange_info = await get_exchange_text(
                stp_repo, exchange, user_id=exchange.seller_id
            )

            seller_message = MESSAGES["payment_date_seller"].format(
                exchange_info=seller_exchange_info
            )

            success = await send_message(
                bot=bot,
                user_id=exchange.seller_id,
                text=seller_message,
                reply_markup=create_basic_keyboard(deeplink),
            )
            if success:
                notifications_sent += 1

        if notifications_sent > 0:
            logger.info(
                f"Отправлено {notifications_sent} уведомлений о дате оплаты для обмена {exchange.id}"
            )

    except Exception as e:
        logger.error(f"Ошибка отправки уведомления о дате оплаты {exchange.id}: {e}")


async def notify_immediate_payment_reminder(
    bot: Bot, stp_repo: MainRequestsRepo, exchange: Exchange
) -> None:
    """Отправка ежедневного напоминания об immediate оплате.

    Args:
        bot: Экземпляр бота
        stp_repo: Репозиторий операций с базой STP
        exchange: Экземпляр сделки
    """
    try:
        # Уведомляем только покупателя о необходимости оплаты
        if not exchange.buyer_id:
            logger.warning(f"Не найден покупатель для обмена {exchange.id}")
            return

        buyer_exchange_info = await get_exchange_text(
            stp_repo, exchange, user_id=exchange.buyer_id
        )

        deeplink = await create_exchange_deeplink(bot, exchange.id)

        message = MESSAGES["immediate_reminder"].format(
            exchange_info=buyer_exchange_info
        )

        success = await send_message(
            bot=bot,
            user_id=exchange.buyer_id,
            text=message,
            reply_markup=create_payment_keyboard(deeplink),
        )

        if success:
            logger.info(
                f"Отправлено напоминание об immediate оплате для обмена {exchange.id}"
            )

    except Exception as e:
        logger.error(
            f"Ошибка отправки напоминания об immediate оплате {exchange.id}: {e}"
        )


async def check_daily_payment_reminders(session_pool, bot: Bot) -> None:
    """Ежедневная проверка и отправка напоминаний об оплате в 12:00.

    Args:
        session_pool: Пул сессий основной БД
        bot: Экземпляр бота
    """
    try:
        async with session_pool() as stp_session:
            stp_repo = MainRequestsRepo(stp_session)

            # Получаем всех пользователей с неоплаченными проданными обменами
            users_with_unpaid_exchanges = (
                await stp_repo.exchange.get_users_with_unpaid_exchanges(
                    status="sold", is_paid=False
                )
            )

            if not users_with_unpaid_exchanges:
                return

            notifications_sent = 0

            for user_data in users_with_unpaid_exchanges:
                try:
                    await notify_daily_payment_reminder(bot, stp_repo, user_data)
                    notifications_sent += 1
                except Exception as e:
                    logger.error(
                        f"Ошибка отправки ежедневного напоминания пользователю {user_data.get('user_id')}: {e}"
                    )

            if notifications_sent > 0:
                logger.info(
                    f"Отправлено {notifications_sent} ежедневных напоминаний об оплате"
                )

    except Exception as e:
        logger.error(f"Ошибка проверки ежедневных напоминаний об оплате: {e}")


async def notify_daily_payment_reminder(
    bot: Bot, stp_repo: MainRequestsRepo, user_data: dict
) -> None:
    """Отправка ежедневного напоминания об оплате пользователю.

    Args:
        bot: Экземпляр бота
        stp_repo: Репозиторий операций с базой STP
        user_data: Данные пользователя с его неоплаченными обменами
    """
    try:
        user_id = user_data["user_id"]
        exchanges = user_data["exchanges"]

        if not exchanges:
            return

        # Формируем информацию о всех неоплаченных обменах
        exchanges_info_list = []
        for exchange in exchanges:
            exchange_info = await get_exchange_text(stp_repo, exchange, user_id=user_id)
            exchanges_info_list.append(f"• {exchange_info}")

        exchanges_info = "\n\n".join(exchanges_info_list)

        # Формируем сообщение
        message = MESSAGES["daily_payment_reminder"].format(
            exchanges_info=exchanges_info
        )

        # Отправляем уведомление (без клавиатуры, так как может быть много обменов)
        success = await send_message(
            bot=bot, user_id=user_id, text=message, disable_notification=False
        )

        if success:
            logger.info(
                f"Отправлено ежедневное напоминание пользователю {user_id} о {len(exchanges)} неоплаченных обменах"
            )

    except Exception as e:
        logger.error(
            f"Ошибка отправки ежедневного напоминания пользователю {user_data.get('user_id')}: {e}"
        )

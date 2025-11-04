import logging
from typing import Any, List

from aiogram import Bot
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from aiogram.utils.deep_linking import create_start_link
from stp_database import Employee, MainRequestsRepo

from tgbot.dialogs.getters.common.exchanges.exchanges import (
    get_exchange_hours,
    get_exchange_text,
)
from tgbot.misc.helpers import tz

logger = logging.getLogger(__name__)


async def handle_exchange_query(
    query_text: str, stp_repo: MainRequestsRepo, user: Employee, bot: Bot
) -> List[InlineQueryResultArticle]:
    """Обработка inline запросов сделок.

    Args:
        query_text: Текст запроса
        stp_repo: Репозиторий операций с базой STP
        user: Экземпляр пользователя с моделью Employee
        bot: Экземпляр бота

    Returns:
        Список найденных сделок
    """
    try:
        exchange_id = query_text.split("_")[1]
        exchange = await stp_repo.exchange.get_exchange_by_id(int(exchange_id))
        if not exchange:
            return []

        # Форматирование информации о сделке
        shift_date, shift_time, price_text = await _format_exchange_info(exchange)

        exchange_info = await get_exchange_text(stp_repo, exchange, user.user_id)
        message_text = f"🔍 <b>Детали сделки</b>\n\n{exchange_info}"

        deeplink = await create_start_link(
            bot=bot, payload=f"exchange_{exchange.id}", encode=True
        )

        return [
            InlineQueryResultArticle(
                id=f"exchange_{exchange.id}",
                title=f"Сделка #{exchange.id}",
                description=f"📅 Предложение: {shift_time} {shift_date} ПРМ\n💰 Цена: {price_text}",
                input_message_content=InputTextMessageContent(
                    message_text=message_text, parse_mode="HTML"
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🎭 Открыть сделку",
                                url=deeplink,
                            )
                        ]
                    ]
                ),
            )
        ]
    except (ValueError, IndexError) as e:
        logger.error(f"[Inline] Ошибка получения информации о сделке: {e}")
        return []


async def _format_exchange_info(exchange: Any) -> tuple[str, str, str]:
    """Форматирование информации о сделке в удобочитаемый вид.

    Args:
        exchange: Экземпляр сделки с моделью Exchange

    Returns:
        Форматированная информация о сделке
    """
    # Обрабатываем время
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

    # Считаем общую стоимость
    exchange_hours = await get_exchange_hours(exchange)
    price_per_hour = exchange.price

    if exchange_hours and price_per_hour:
        total_price = int(price_per_hour * exchange_hours)
        price_text = f"{price_per_hour:g} р./ч. ({total_price:g} р.)"
    else:
        price_text = f"{price_per_hour:g} р./ч." if price_per_hour else "Не указано"

    return shift_date, shift_time, price_text


async def handle_user_exchanges(
    stp_repo: MainRequestsRepo, user: Employee, bot: Bot
) -> List[InlineQueryResultArticle]:
    """Обработка inline запросов пользовательских сделок.

    Args:
        stp_repo: Репозиторий операций с базой STP
        user: Экземпляр пользователя с моделью Employee
        bot: Экземпляр бота

    Returns:
        Список активных сделок пользователя
    """
    try:
        # Получаем активные сделки пользователя
        exchanges = await stp_repo.exchange.get_user_exchanges(
            user.user_id, status="active"
        )

        if not exchanges:
            return [
                InlineQueryResultArticle(
                    id="no_exchanges",
                    title="📭 Нет активных сделок",
                    description="У тебя пока нет активных сделок",
                    input_message_content=InputTextMessageContent(
                        message_text="📭 <b>Нет активных сделок</b>\n\nУ тебя пока нет активных сделок.",
                        parse_mode="HTML",
                    ),
                )
            ]

        results = []
        for exchange in exchanges:
            # Форматирование информации о сделке
            shift_date, shift_time, price_text = await _format_exchange_info(exchange)

            exchange_info = await get_exchange_text(stp_repo, exchange, user.user_id)
            message_text = f"🔍 <b>Детали сделки</b>\n\n{exchange_info}"

            deeplink = await create_start_link(
                bot=bot, payload=f"exchange_{exchange.id}", encode=True
            )

            # Определяем статус сделки для иконки
            status_icon = "🟢" if exchange.status == "active" else "🟡"

            results.append(
                InlineQueryResultArticle(
                    id=f"user_exchange_{exchange.id}",
                    title=f"{status_icon} Сделка #{exchange.id}",
                    description=f"📅 {shift_time} {shift_date} ПРМ\n💰 {price_text}",
                    input_message_content=InputTextMessageContent(
                        message_text=message_text, parse_mode="HTML"
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="🎭 Открыть сделку",
                                    url=deeplink,
                                )
                            ]
                        ]
                    ),
                )
            )

        return results

    except Exception as e:
        logger.error(f"[Inline] Ошибка получения пользовательских сделок: {e}")
        return [
            InlineQueryResultArticle(
                id="exchanges_error",
                title="❌ Ошибка",
                description="Не удалось загрузить твои сделки",
                input_message_content=InputTextMessageContent(
                    message_text="❌ <b>Ошибка</b>\n\nНе удалось загрузить твои сделки",
                    parse_mode="HTML",
                ),
            )
        ]

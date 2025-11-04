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
from stp_database import MainRequestsRepo

from tgbot.handlers.inline.helpers import DAY_NAMES, EXCHANGE_TYPE_NAMES

logger = logging.getLogger(__name__)


async def handle_subscription_query(
    query_text: str, stp_repo: MainRequestsRepo, bot: Bot
) -> List[InlineQueryResultArticle]:
    """Обработка inline запросов подписок на сделки.

    Args:
        query_text: Текст запроса
        stp_repo: Репозиторий операций с базой STP
        bot: Экземпляр бота

    Returns:
        Список найденных подписок
    """
    try:
        subscription_id = query_text.split("_")[1]
        subscription = await stp_repo.exchange.get_subscription_by_id(
            int(subscription_id)
        )
        if not subscription:
            return []

        # Форматирование информации о подписке
        exchange_type = EXCHANGE_TYPE_NAMES.get(
            subscription.exchange_type, subscription.exchange_type
        )
        criteria_text = _format_subscription_criteria(subscription)

        message_text = f"""🔍 <b>Детали подписки</b>

📝 <b>Название:</b> {subscription.name}
<b>Тип обменов:</b> {exchange_type}

🎯 <b>Критерии:</b>
{criteria_text}"""

        deeplink = await create_start_link(
            bot=bot, payload=f"subscription_{subscription.id}", encode=True
        )

        return [
            InlineQueryResultArticle(
                id=f"subscription_{subscription_id}",
                title=f"🔔 Подписка {subscription.id}",
                description=f"Тип обменов: {exchange_type}\n🎯 Критерии:\n{criteria_text}",
                input_message_content=InputTextMessageContent(
                    message_text=message_text, parse_mode="HTML"
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🔔 Добавить подписку",
                                url=deeplink,
                            )
                        ]
                    ]
                ),
            )
        ]
    except (ValueError, IndexError) as e:
        logger.error(f"[Inline] Ошибка получения информации о подписке: {e}")
        return []


def _format_subscription_criteria(subscription: Any) -> str:
    """Форматирование информации о подписке в удобочитаемый вид.

    Args:
        subscription: Экземпляр подписки с моделью Subscription

    Returns:
        Форматированная информация о подписке
    """
    criteria_parts = []

    if subscription.min_price:
        criteria_parts.append(f"• Минимальная цена: {subscription.min_price} р.")
    if subscription.max_price:
        criteria_parts.append(f"• Максимальная цена: {subscription.max_price} р.")
    if subscription.start_time and subscription.end_time:
        criteria_parts.append(
            f"• Время: с {subscription.start_time.strftime('%H:%M')} "
            f"до {subscription.end_time.strftime('%H:%M')}"
        )
    if subscription.days_of_week:
        days_text = ", ".join([
            DAY_NAMES.get(d, str(d)) for d in subscription.days_of_week
        ])
        criteria_parts.append(f"• Дни: {days_text}")

    return "\n".join(criteria_parts) if criteria_parts else "• Все обмены"

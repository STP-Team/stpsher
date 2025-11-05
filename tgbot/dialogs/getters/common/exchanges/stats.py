"""Геттеры для окон статистики сделок."""

import logging
from typing import Any, Dict

from stp_database import Employee, MainRequestsRepo

logger = logging.getLogger(__name__)


async def stats_getter(
    stp_repo: MainRequestsRepo, user: Employee, **_kwargs
) -> Dict[str, Any]:
    """Геттер для общей статистики по сделкам.

    Args:
        stp_repo: Репозиторий операций с базой STP
        user: Экземпляр пользователя с моделью Employee

    Returns:
        Словарь с базовой статистикой сделок пользователя
    """
    # Получаем все обмены пользователя
    user_exchanges = await stp_repo.exchange.get_user_exchanges(
        user_id=user.user_id,
        limit=1000,
    )

    total_exchanges = len(user_exchanges)

    # Подсчёт по типам
    owned_exchanges = [ex for ex in user_exchanges if ex.owner_id == user.user_id]
    owner_sell_count = len([ex for ex in owned_exchanges if ex.owner_intent == "sell"])
    owner_buy_count = len([ex for ex in owned_exchanges if ex.owner_intent == "buy"])

    participant_buy_count = len([
        ex
        for ex in user_exchanges
        if ex.counterpart_id == user.user_id and ex.owner_intent == "sell"
    ])
    participant_sell_count = len([
        ex
        for ex in user_exchanges
        if ex.counterpart_id == user.user_id and ex.owner_intent == "buy"
    ])

    total_loss = await stp_repo.exchange.get_user_total_loss(user.user_id)
    total_gain = await stp_repo.exchange.get_user_total_gain(user.user_id)

    # Возвращаем все данные
    result = {
        "total_exchanges": total_exchanges,
        "has_exchanges": total_exchanges > 0,
        # Основные счетчики
        "owner_sell": owner_sell_count,
        "owner_buy": owner_buy_count,
        "counterpart_buy": participant_buy_count,
        "counterpart_sell": participant_sell_count,
        # Общие суммы
        "total_loss": f"{total_loss:g}",
        "total_gain": f"{total_gain:g}",
    }

    return result

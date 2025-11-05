"""Сервис для получения статистики по биржевым сделкам."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy import and_, func, select
from stp_database import MainRequestsRepo
from stp_database.models.STP.exchange import Exchange

logger = logging.getLogger(__name__)


async def get_market_average_prices(
    repo: MainRequestsRepo, intent: str = "all"
) -> Dict[str, Any]:
    """Получение средних рыночных цен за последнюю неделю и месяц.

    Args:
        repo: Репозиторий для работы с базой данных
        intent: Тип сделок - "sell", "buy" или "all"

    Returns:
        Словарь со средними ценами за неделю и месяц
    """
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    try:
        # Базовые условия фильтрации для недели
        week_conditions = [
            Exchange.status == "active",
            Exchange.created_at >= week_ago,
            Exchange.created_at <= now,
        ]

        # Добавляем фильтр по типу сделки если нужно
        if intent != "all":
            week_conditions.append(Exchange.owner_intent == intent)

        # Средняя цена за последнюю неделю
        week_query = select(
            func.avg(Exchange.price).label("average_price"),
            func.count(Exchange.id).label("total_count"),
        ).where(and_(*week_conditions))

        week_result = await repo.session.execute(week_query)
        week_row = week_result.first()

        # Базовые условия фильтрации для месяца
        month_conditions = [
            Exchange.status == "active",
            Exchange.created_at >= month_ago,
            Exchange.created_at <= now,
        ]

        if intent != "all":
            month_conditions.append(Exchange.owner_intent == intent)

        # Средняя цена за последний месяц
        month_query = select(
            func.avg(Exchange.price).label("average_price"),
            func.count(Exchange.id).label("total_count"),
        ).where(and_(*month_conditions))

        month_result = await repo.session.execute(month_query)
        month_row = month_result.first()

        # Форматируем результаты
        week_average = (
            round(float(week_row.average_price or 0), 0)
            if week_row.average_price
            else 0
        )
        month_average = (
            round(float(month_row.average_price or 0), 0)
            if month_row.average_price
            else 0
        )

        result = {
            "week": {
                "average_price": int(week_average),
                "count": week_row.total_count or 0,
            },
            "month": {
                "average_price": int(month_average),
                "count": month_row.total_count or 0,
            },
            "intent": intent,
        }

        logger.info(
            f"[Биржа] Получена статистика цен ({intent}): неделя={week_average}р. ({week_row.total_count}), месяц={month_average}р. ({month_row.total_count})"
        )
        return result

    except Exception as e:
        logger.error(f"[Биржа] Ошибка получения рыночной статистики: {e}")
        return {
            "week": {"average_price": 0, "count": 0},
            "month": {"average_price": 0, "count": 0},
            "intent": intent,
        }


def format_market_stats_text(stats: Dict[str, Any]) -> str:
    """Форматирование статистики в удобочитаемый текст.

    Args:
        stats: Словарь со статистикой от get_market_average_prices

    Returns:
        Отформатированная строка для отображения пользователю
    """
    week_price = stats["week"]["average_price"]
    week_count = stats["week"]["count"]
    month_price = stats["month"]["average_price"]
    month_count = stats["month"]["count"]

    lines = []

    if week_count > 0:
        lines.append(
            f"📈 <b>Средняя цена за неделю:</b> {week_price} р./ч. ({week_count})"
        )
    else:
        lines.append("📈 <b>За неделю:</b> нет данных")

    if month_count > 0:
        lines.append(
            f"📊 <b>Средняя цена за месяц:</b> {month_price} р./ч. ({month_count})"
            f"📊 <b>Средняя цена за месяц:</b> {month_price} р./ч. ({month_count})"
        )
    else:
        lines.append("📊 <b>За месяц:</b> нет данных")

    if not lines:
        return "\n<i>Статистика недоступна</i>"

    return "\n" + "\n".join(lines)


async def get_combined_market_stats(repo: MainRequestsRepo) -> Dict[str, Any]:
    """Получение комбинированной статистики для главного меню (покупка и продажа).

    Args:
        repo: Репозиторий для работы с базой данных

    Returns:
        Словарь с комбинированной статистикой
    """
    sell_stats = await get_market_average_prices(repo, "sell")
    buy_stats = await get_market_average_prices(repo, "buy")

    return {"sell": sell_stats, "buy": buy_stats}


def format_combined_market_stats_text(combined_stats: Dict[str, Any]) -> str:
    """Форматирование комбинированной статистики для главного меню.

    Args:
        combined_stats: Словарь с комбинированной статистикой

    Returns:
        Отформатированная строка для отображения пользователю
    """
    sell_stats = combined_stats["sell"]
    buy_stats = combined_stats["buy"]

    lines = []

    # Статистика продаж (что можно купить)
    sell_week_price = sell_stats["week"]["average_price"]
    sell_week_count = sell_stats["week"]["count"]
    sell_month_price = sell_stats["month"]["average_price"]
    sell_month_count = sell_stats["month"]["count"]

    if sell_week_count > 0 or sell_month_count > 0:
        lines.append("<b>📉 Продажи:</b>")
        if sell_week_count > 0:
            lines.append(f"Неделя: {sell_week_price} р./ч. ({sell_week_count})")
        else:
            lines.append("Неделя: нет данных")

        if sell_month_count > 0:
            lines.append(f"Месяц: {sell_month_price} р./ч. ({sell_month_count})")
        else:
            lines.append("Месяц: нет данных")

    # Статистика покупок (что хотят купить)
    buy_week_price = buy_stats["week"]["average_price"]
    buy_week_count = buy_stats["week"]["count"]
    buy_month_price = buy_stats["month"]["average_price"]
    buy_month_count = buy_stats["month"]["count"]

    if buy_week_count > 0 or buy_month_count > 0:
        if lines:  # Добавляем пустую строку если уже есть данные о продажах
            lines.append("")
        lines.append("<b>📈 Покупки:</b>")
        if buy_week_count > 0:
            lines.append(f"Неделя: {buy_week_price} р./ч. ({buy_week_count})")
        else:
            lines.append("Неделя: нет данных")

        if buy_month_count > 0:
            lines.append(f"Месяц: {buy_month_price} р./ч. ({buy_month_count})")
        else:
            lines.append("Месяц: нет данных")

    if not lines:
        return "\n<i>Статистика недоступна</i>"

    return "\n" + "\n".join(lines)


def format_intent_specific_stats_text(stats: Dict[str, Any], context: str) -> str:
    """Форматирование статистики для конкретного контекста (buy/sell).

    Args:
        stats: Словарь со статистикой от get_market_average_prices
        context: Контекст - "buy_dialog" или "sell_dialog"

    Returns:
        Отформатированная строка для отображения пользователю
    """
    week_price = stats["week"]["average_price"]
    week_count = stats["week"]["count"]
    month_price = stats["month"]["average_price"]
    month_count = stats["month"]["count"]

    lines = []

    # Определяем заголовок в зависимости от контекста
    if context == "buy_dialog":
        header = "<b>📉 Предложения продаж:</b>"
    elif context == "sell_dialog":
        header = "<b>📈 Запросы покупок:</b>"
    else:
        header = "<b>Рыночная статистика:</b>"

    lines.append(header)

    if week_count > 0:
        lines.append(f"Неделя: {week_price} р./ч. ({week_count})")
    else:
        lines.append("Неделя: нет данных")

    if month_count > 0:
        lines.append(f"Месяц: {month_price} р./ч. ({month_count})")
    else:
        lines.append("Месяц: нет данных")

    return "\n" + "\n".join(lines)

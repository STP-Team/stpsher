"""Геттеры для окон статистики сделок."""

import logging
from datetime import datetime
from typing import Any, Dict

from aiogram import Bot
from aiogram.utils.deep_linking import create_start_link
from stp_database.models.STP import Employee
from stp_database.repo.STP import MainRequestsRepo

from tgbot.misc.dicts import months_emojis, russian_months
from tgbot.misc.helpers import format_fullname
from tgbot.services.files_processing.utils.time_parser import get_current_month

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
        user_id=user.user_id, limit=1000, status="sold"
    )

    total_exchanges = len(user_exchanges)

    # Подсчёт общих покупок и продаж пользователя
    # Покупки: когда пользователь создал сделку на покупку ИЛИ откликнулся на продажу
    total_buy_count = len([
        ex
        for ex in user_exchanges
        if (ex.owner_id == user.user_id and ex.owner_intent == "buy")
        or (ex.counterpart_id == user.user_id and ex.owner_intent == "sell")
    ])

    # Продажи: когда пользователь создал сделку на продажу ИЛИ откликнулся на покупку
    total_sell_count = len([
        ex
        for ex in user_exchanges
        if (ex.owner_id == user.user_id and ex.owner_intent == "sell")
        or (ex.counterpart_id == user.user_id and ex.owner_intent == "buy")
    ])

    total_income = await stp_repo.exchange.get_user_total_gain(user.user_id)
    total_expenses = await stp_repo.exchange.get_user_total_loss(user.user_id)
    net_profit = total_income - total_expenses

    # Получаем общее количество проданных и купленных часов
    total_hours_sold = await stp_repo.exchange.get_user_total_hours_sold(user.user_id)
    total_hours_bought = await stp_repo.exchange.get_user_total_hours_bought(
        user.user_id
    )
    total_exchanged_hours = total_hours_bought + total_hours_sold

    avg_sell_price = await stp_repo.exchange.get_user_overall_avg_sell_price(
        user_id=user.user_id
    )

    avg_buy_price = await stp_repo.exchange.get_user_overall_avg_buy_price(
        user_id=user.user_id
    )

    # Получаем топ-5 покупателей и продавцов за все время
    top_buyers_data = await stp_repo.exchange.get_user_top_buyers(
        user_id=user.user_id, limit=5
    )
    top_sellers_data = await stp_repo.exchange.get_user_top_sellers(
        user_id=user.user_id, limit=5
    )

    # Форматируем информацию о покупателях
    top_buyers_text = ""
    if top_buyers_data:
        buyers_list = []
        for i, buyer in enumerate(top_buyers_data, 1):
            buyer_user = await stp_repo.employee.get_users(user_id=buyer["buyer_id"])
            buyer_name = format_fullname(buyer_user, True, True)
            buyers_list.append(
                f"{i}. <b>{buyer_name}</b>: {buyer['total_amount']:g} ₽ ({buyer['total_purchases']} сделок)"
            )
        top_buyers_text = "\n".join(buyers_list)

    # Форматируем информацию о продавцах
    top_sellers_text = ""
    if top_sellers_data:
        sellers_list = []
        for i, seller in enumerate(top_sellers_data, 1):
            seller_user = await stp_repo.employee.get_users(user_id=seller["seller_id"])
            seller_name = format_fullname(seller_user, True, True)
            sellers_list.append(
                f"{i}. <b>{seller_name}</b>: {seller['total_amount']:g} ₽ ({seller['total_sales_to_user']} сделок)"
            )
        top_sellers_text = "\n".join(sellers_list)

    # Возвращаем все данные
    result = {
        "total_exchanges": total_exchanges,
        "has_exchanges": total_exchanges > 0,
        # Общие счетчики покупок и продаж
        "total_buy": total_buy_count,
        "total_sell": total_sell_count,
        # Общие суммы
        "total_income": f"{total_income:g}",
        "total_expenses": f"{total_expenses:g}",
        "net_profit": f"{net_profit:g}",
        # Общее количество часов
        "total_hours_sold": f"{total_hours_sold:g}",
        "total_hours_bought": f"{total_hours_bought:g}",
        "total_exchanged_hours": f"{total_exchanged_hours:g}",
        # Средние значения
        "avg_sell_price": f"{avg_sell_price:g}",
        "avg_buy_price": f"{avg_buy_price:g}",
        # Топ партнеры
        "top_buyers": top_buyers_text,
        "top_sellers": top_sellers_text,
        "has_top_buyers": len(top_buyers_data) > 0,
        "has_top_sellers": len(top_sellers_data) > 0,
    }

    return result


async def finances_getter(
    stp_repo: MainRequestsRepo, user: Employee, dialog_manager, bot: Bot, **_kwargs
) -> Dict[str, Any]:
    """Геттер для финансовой статистики сделок с фильтрацией по месяцам.

    Args:
        stp_repo: Репозиторий операций с базой STP
        user: Экземпляр пользователя с моделью Employee
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с финансовой статистикой сделок пользователя за выбранный месяц
    """
    # Получаем выбранный месяц из dialog_data или используем текущий
    current_month = dialog_manager.dialog_data.get("current_month", get_current_month())

    month_emoji = months_emojis.get(current_month.lower(), "📅")

    # Получаем номер месяца
    month_to_num = {name: num for num, name in russian_months.items()}
    month_num = month_to_num.get(current_month.lower(), datetime.now().month)

    # Определяем год (если выбранный месяц больше текущего, то это прошлый год)
    current_year = datetime.now().year
    current_month_num = datetime.now().month

    if month_num > current_month_num:
        year = current_year - 1
    else:
        year = current_year

    # Создаем диапазон дат для выбранного месяца
    start_date = datetime(year, month_num, 1)

    # Конец месяца
    if month_num == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month_num + 1, 1)

    # Получаем финансовую статистику за период
    total_income = await stp_repo.exchange.get_user_total_gain(
        user_id=user.user_id, start_date=start_date, end_date=end_date
    )

    total_expenses = await stp_repo.exchange.get_user_total_loss(
        user_id=user.user_id, start_date=start_date, end_date=end_date
    )

    # Получаем статистику продаж и покупок
    sales_stats = await stp_repo.exchange.get_sales_stats_for_period(
        user_id=user.user_id, start_date=start_date, end_date=end_date
    )

    purchases_stats = await stp_repo.exchange.get_purchases_stats_for_period(
        user_id=user.user_id, start_date=start_date, end_date=end_date
    )

    # Подсчитываем общие показатели
    total_deals = sales_stats.get("total_sales", 0) + purchases_stats.get(
        "total_purchases", 0
    )
    net_profit = total_income - total_expenses

    # Экстремальные сделки (найдем самые дорогие продажи и покупки)
    # Получаем все сделки за период для анализа экстремумов
    user_exchanges = await stp_repo.exchange.get_exchanges_by_date_range(
        start_date=start_date, end_date=end_date, status="sold"
    )

    # Фильтруем только сделки пользователя
    user_period_exchanges = [
        ex
        for ex in user_exchanges
        if ex.owner_id == user.user_id or ex.counterpart_id == user.user_id
    ]

    # Топ-3 продаж и покупок
    top_sells_text = ""
    top_buys_text = ""
    has_top_sells = False
    has_top_buys = False

    if user_period_exchanges:
        exchanges_with_prices = [ex for ex in user_period_exchanges if ex.total_price]

        if exchanges_with_prices:
            # Продажи пользователя
            user_sells = [
                ex
                for ex in exchanges_with_prices
                if (ex.owner_id == user.user_id and ex.owner_intent == "sell")
                or (ex.counterpart_id == user.user_id and ex.owner_intent == "buy")
            ]

            # Покупки пользователя
            user_buys = [
                ex
                for ex in exchanges_with_prices
                if (ex.owner_id == user.user_id and ex.owner_intent == "buy")
                or (ex.counterpart_id == user.user_id and ex.owner_intent == "sell")
            ]

            # Топ-3 продаж
            if user_sells:
                top_sells = sorted(
                    user_sells, key=lambda x: x.total_price, reverse=True
                )[:3]
                sells_list = []
                for i, exchange in enumerate(top_sells, 1):
                    deeplink = await create_start_link(
                        bot=bot, payload=f"exchange_{exchange.id}", encode=True
                    )
                    # Форматируем дату
                    start_date = (
                        exchange.start_time.strftime("%d.%m.%Y")
                        if exchange.start_time
                        else "Без даты"
                    )
                    # Получаем часы работы
                    hours = (
                        f"({exchange.working_hours:g} ч.)"
                        if exchange.working_hours
                        else ""
                    )
                    sells_list.append(
                        f"{i}. <a href='{deeplink}'><b>{start_date} {hours} {exchange.total_price:g} ₽</b></a>"
                    )
                if sells_list:
                    top_sells_text = "\n".join(sells_list)
                    has_top_sells = True

            # Топ-3 покупок
            if user_buys:
                top_buys = sorted(user_buys, key=lambda x: x.total_price, reverse=True)[
                    :3
                ]
                buys_list = []
                for i, exchange in enumerate(top_buys, 1):
                    deeplink = await create_start_link(
                        bot=bot, payload=f"exchange_{exchange.id}", encode=True
                    )
                    # Форматируем дату
                    start_date = (
                        exchange.start_time.strftime("%d.%m.%Y")
                        if exchange.start_time
                        else "Без даты"
                    )
                    # Получаем часы работы
                    hours = (
                        f"({exchange.working_hours:g} ч.)"
                        if exchange.working_hours
                        else ""
                    )
                    buys_list.append(
                        f"{i}. <a href='{deeplink}'><b>{start_date} {hours} {exchange.total_price:g} ₽</b></a>"
                    )
                if buys_list:
                    top_buys_text = "\n".join(buys_list)
                    has_top_buys = True

    # Возвращаем все данные
    result = {
        "month_display": f"{month_emoji} {current_month.capitalize()}",
        "period_text": f"за {current_month.lower()} {year}",
        "stats_type_financial": True,
        "has_exchanges": total_deals > 0,
        "has_top_sells": has_top_sells,
        "has_top_buys": has_top_buys,
        "total_income": f"{total_income:g}",
        "total_expenses": f"{total_expenses:g}",
        "net_profit": f"{net_profit:g}",
        "top_sells_text": top_sells_text,
        "top_buys_text": top_buys_text,
    }

    # Получаем средние цены за месяц
    avg_sell_price = await stp_repo.exchange.get_user_monthly_avg_sell_price(
        user_id=user.user_id, year=year, month=month_num
    )

    avg_buy_price = await stp_repo.exchange.get_user_monthly_avg_buy_price(
        user_id=user.user_id, year=year, month=month_num
    )

    # Получаем топ-5 покупателей и продавцов за выбранный месяц
    top_buyers_month_data = await stp_repo.exchange.get_user_top_buyers(
        user_id=user.user_id, start_date=start_date, end_date=end_date, limit=5
    )
    top_sellers_month_data = await stp_repo.exchange.get_user_top_sellers(
        user_id=user.user_id, start_date=start_date, end_date=end_date, limit=5
    )

    # Форматируем информацию о покупателях за месяц
    top_buyers_month_text = ""
    if top_buyers_month_data:
        buyers_list = []
        for i, buyer in enumerate(top_buyers_month_data, 1):
            buyer_user = await stp_repo.employee.get_users(user_id=buyer["buyer_id"])
            buyer_name = format_fullname(buyer_user, True, True)
            buyers_list.append(
                f"{i}. <b>{buyer_name}</b>: {buyer['total_amount']:g} ₽ ({buyer['total_purchases']} сделок)"
            )
        top_buyers_month_text = "\n".join(buyers_list)

    # Форматируем информацию о продавцах за месяц
    top_sellers_month_text = ""
    if top_sellers_month_data:
        sellers_list = []
        for i, seller in enumerate(top_sellers_month_data, 1):
            seller_user = await stp_repo.employee.get_users(user_id=seller["seller_id"])
            seller_name = format_fullname(seller_user, True, True)
            sellers_list.append(
                f"{i}. <b>{seller_name}</b>: {seller['total_amount']:g} ₽ ({seller['total_sales_to_user']} сделок)"
            )
        top_sellers_month_text = "\n".join(sellers_list)

    # Добавляем в результат
    result.update({
        "avg_sell_price": f"{avg_sell_price:g}",
        "avg_buy_price": f"{avg_buy_price:g}",
        # Топ партнеры за месяц
        "top_buyers_month": top_buyers_month_text,
        "top_sellers_month": top_sellers_month_text,
        "has_top_buyers_month": len(top_buyers_month_data) > 0,
        "has_top_sellers_month": len(top_sellers_month_data) > 0,
    })

    return result

"""Геттеры для биржи подмен."""

import logging
import re
from datetime import datetime
from typing import Any, Dict

from aiogram import Bot
from aiogram.utils.deep_linking import create_start_link
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import ManagedCheckbox
from stp_database import Employee, Exchange, MainRequestsRepo

from tgbot.misc.dicts import exchange_emojis
from tgbot.misc.helpers import format_fullname, strftime_date, tz
from tgbot.services.files_processing.parsers.schedule import (
    DutyScheduleParser,
    ScheduleParser,
)

logger = logging.getLogger(__name__)


def get_month_name(month_number: int) -> str:
    """Получить название месяца на русском языке."""
    months = [
        "",
        "Январь",
        "Февраль",
        "Март",
        "Апрель",
        "Май",
        "Июнь",
        "Июль",
        "Август",
        "Сентябрь",
        "Октябрь",
        "Ноябрь",
        "Декабрь",
    ]
    return months[month_number] if 1 <= month_number <= 12 else "Неизвестно"


async def prepare_calendar_data_for_exchange(
    stp_repo: MainRequestsRepo, user: Employee, dialog_manager: DialogManager
) -> None:
    """Подготавливает данные календаря с информацией о сменах пользователя."""
    try:
        # Получаем текущий месяц для календаря
        current_date = datetime.now().date()

        parser = ScheduleParser()
        month_name = get_month_name(current_date.month)

        # Получаем график пользователя на текущий месяц
        try:
            schedule_dict = await parser.get_user_schedule_with_duties(
                user.fullname,
                month_name,
                user.division,
                stp_repo,
                current_day_only=False,
            )

            # Извлекаем дни когда есть смены
            shift_dates = {}
            for day, (schedule, duty_info) in schedule_dict.items():
                if schedule and schedule not in ["Не указано", "В", "О"]:
                    # Извлекаем номер дня
                    day_match = re.search(r"(\d{1,2})", day)
                    if day_match:
                        day_num = f"{int(day_match.group(1)):02d}"
                        shift_dates[day_num] = {
                            "schedule": schedule,
                            "duty_info": duty_info,
                        }

            # Сохраняем данные в dialog_data для использования в календаре
            dialog_manager.dialog_data["shift_dates"] = shift_dates

        except Exception:
            # В случае ошибки просто не показываем смены
            dialog_manager.dialog_data["shift_dates"] = {}

    except Exception:
        # В случае ошибки просто не показываем смены
        dialog_manager.dialog_data["shift_dates"] = {}


async def get_exchange_shift_time(start_time: str, end_time: str):
    # Извлекаем только время из datetime строк
    start_time_str = start_time.split("T")[1][:5] if "T" in start_time else start_time
    end_time_str = end_time.split("T")[1][:5] if "T" in end_time else end_time

    shift_time = f"{start_time_str}-{end_time_str}"
    return shift_time


async def get_exchange_type(exchange: Exchange, is_seller: bool) -> str:
    """Получает тип сделки.

    Args:
        exchange:
        is_seller:

    Returns:
        Тип сделки: "📉 Продам" или "📈 Куплю"
    """
    if exchange.type == "sell":
        operation_type = "📉 Продам"
    else:
        operation_type = "📈 Куплю"

    return operation_type


async def get_exchange_status(exchange: Exchange) -> str:
    """Получает статус сделки.

    Args:
        exchange: Экземпляр сделки с моделью Exchange

    Returns:
        Статус сделки
    """
    if exchange.status == "active":
        status = f"{exchange_emojis['active']} Активная"
    elif exchange.status == "sold":
        status = f"{exchange_emojis['sold']} Завершена"
    elif exchange.status == "canceled":
        status = f"{exchange_emojis['canceled']} Отменена"
    elif exchange.status == "expired":
        status = f"{exchange_emojis['expired']} Истекшая"
    else:
        status = f"ℹ️ {exchange.status.title()}"

    return status


async def get_exchange_hours(exchange: Exchange) -> float | None:
    """Расчет кол-ва часов сделки.

    Args:
        exchange: Экземпляр сделки с моделью Exchange

    Returns:
        Кол-во часов или None
    """
    if exchange.start_time and exchange.end_time:
        try:
            # Рассчитываем продолжительность из TIMESTAMP полей
            duration = exchange.end_time - exchange.start_time
            exchange_hours = duration.total_seconds() / 3600  # Переводим в часы
            return exchange_hours
        except Exception as e:
            logger.error(f"[Биржа] Ошибка расчета часов сделки: {e}")
            return None


async def get_exchange_price_per_hour(exchange: Exchange):
    """Расчет стоимости одного часа в сделке.

    Args:
        exchange: Экземпляр сделки с моделью Exchange

    Returns:
        Стоимость одного часа
    """
    price = 0
    exchange_hours = await get_exchange_hours(exchange)

    if exchange_hours and exchange_hours > 0 and exchange.price:
        price = round(exchange.price / exchange_hours, 2)

    return price


async def get_exchange_text(
    stp_repo: MainRequestsRepo, exchange: Exchange, user_id: int
) -> str:
    """Форматирует текст для отображения базовой информации о сделке.

    Args:
        exchange: Экземпляр сделки с моделью Exchange
        user_id: Идентификатор Telegram

    Returns:
        Форматированная строка
    """
    exchange_type = await get_exchange_type(
        exchange, is_seller=exchange.seller_id == user_id
    )

    # Защита от None значений в датах/времени
    if exchange.start_time:
        shift_date = exchange.start_time.strftime("%d.%m.%Y")
        start_time_str = exchange.start_time.strftime("%H:%M")
    else:
        shift_date = "Не указано"
        start_time_str = "Не указано"

    if exchange.end_time:
        end_time_str = exchange.end_time.strftime("%H:%M")
    else:
        end_time_str = "Не указано"

    shift_time = f"{start_time_str}-{end_time_str}"
    shift_hours = await get_exchange_hours(exchange)
    price = exchange.price

    # Защита от None значений в часах
    hours_text = f"{shift_hours:g} ч." if shift_hours is not None else "Не указано"

    if exchange.type == "sell":
        seller = await stp_repo.employee.get_users(user_id=exchange.seller_id)
        seller_name = format_fullname(
            seller.fullname, True, True, seller.username, seller.username
        )
        price_per_hour = await get_exchange_price_per_hour(exchange)
        price_per_hour_text = (
            f"{price_per_hour:g} р./ч." if price_per_hour is not None else "Не указано"
        )
        exchange_text = f"""<blockquote><b>{exchange_type}:</b>
<code>{shift_time} ({hours_text}) {shift_date} ПРМ</code>
💰 <b>Цена:</b>
<code>{price:g} р. ({price_per_hour_text})</code> {"сразу" if exchange.payment_type == "immediate" else exchange.payment_date}
👤 <b>Продавец:</b> 
{seller_name}</blockquote>"""
    else:
        buyer = await stp_repo.employee.get_users(user_id=exchange.buyer_id)
        buyer_name = format_fullname(
            buyer.fullname, True, True, buyer.username, buyer.username
        )
        exchange_text = f"""<blockquote><b>{exchange_type}:</b>
<code>{shift_time} ({hours_text}) {shift_date} ПРМ</code>
💰 <b>Цена:</b>
<code>{price:g} р./ч.</code> {"сразу" if exchange.payment_type == "immediate" else exchange.payment_date}
👤 <b>Продавец:</b>
{buyer_name}</blockquote>"""
    return exchange_text


async def exchanges_getter(user: Employee, **_kwargs):
    """Геттер для главного меню подмен.

    Args:
        user: Экземпляр пользователя с моделью Employee.

    Returns:
        True если сотрудник из НЦК, иначе False
    """
    return {"is_nck": user.division == "НЦК"}


async def exchange_buy_getter(
    stp_repo: MainRequestsRepo, user: Employee, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна покупки часов.

    Показывает предложения продаж (то, что мы можем купить).

    Args:
        stp_repo: Репозиторий операций с базой STP
        user: Экземпляр пользователя с моделью Employee
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с доступными сделками
    """
    from datetime import date

    from aiogram_dialog.widgets.kbd import ManagedRadio, ManagedToggle

    user_id = dialog_manager.event.from_user.id

    try:
        # Получаем сделки продаж (то, что другие продают и мы можем купить)
        exchanges = await stp_repo.exchange.get_active_exchanges(
            exclude_user_id=user_id,
            division="НЦК" if user.division == "НЦК" else ["НТП1", "НТП2"],
            exchange_type="sell",
        )

        # Получаем настройки фильтрации и сортировки
        day_filter_checkbox: ManagedRadio = dialog_manager.find("day_filter")
        day_filter_value = (
            day_filter_checkbox.get_checked() if day_filter_checkbox else "all"
        )

        shift_filter_checkbox: ManagedRadio = dialog_manager.find("shift_filter")
        shift_filter_value = (
            shift_filter_checkbox.get_checked() if shift_filter_checkbox else "all"
        )

        date_sort_toggle: ManagedToggle = dialog_manager.find("date_sort")
        date_sort_value = (
            date_sort_toggle.get_checked() if date_sort_toggle else "nearest"
        )

        price_sort_toggle: ManagedToggle = dialog_manager.find("price_sort")
        price_sort_value = (
            price_sort_toggle.get_checked() if price_sort_toggle else "cheap"
        )

        # Применяем фильтры
        from datetime import timedelta

        filtered_exchanges = []
        today = date.today()
        tomorrow = today + timedelta(days=1)

        for exchange in exchanges:
            exchange_date = exchange.start_time.date()

            # Фильтр по дням
            if day_filter_value == "today" and exchange_date != today:
                continue
            elif day_filter_value == "tomorrow" and exchange_date != tomorrow:
                continue

            # Фильтр по сменам (пока не реализован функционал определения смен)
            # Можно добавить логику определения наличия смены по времени
            if shift_filter_value == "no_shift":
                # Условно считаем, что смены с 8:00 до 20:00 - это дневные смены
                start_hour = exchange.start_time.hour
                if 8 <= start_hour <= 20:
                    continue
            elif shift_filter_value == "shift":
                start_hour = exchange.start_time.hour
                if not (8 <= start_hour <= 20):
                    continue

            filtered_exchanges.append(exchange)

        # Применяем сортировку
        # Используем составной ключ сортировки для корректной работы с несколькими критериями
        def sort_key(exchange):
            # Определяем направление сортировки для даты
            date_multiplier = 1 if date_sort_value == "nearest" else -1
            # Определяем направление сортировки для цены
            price_multiplier = 1 if price_sort_value == "cheap" else -1

            # Возвращаем кортеж (дата, цена) с учетом направления сортировки
            # Используем timestamp для корректной обработки отрицательных значений
            return (
                date_multiplier * exchange.start_time.timestamp(),
                price_multiplier * exchange.price,
            )

        filtered_exchanges.sort(key=sort_key)

        # Форматируем данные для отображения
        available_exchanges = []
        for exchange in filtered_exchanges:
            # Форматируем время из start_time и end_time с защитой от None
            if exchange.start_time and exchange.end_time:
                time_str = f"{exchange.start_time.strftime('%H:%M')}-{exchange.end_time.strftime('%H:%M')}"
            elif exchange.start_time:
                time_str = f"{exchange.start_time.strftime('%H:%M')}-Не указано"
            else:
                time_str = "Не указано"

            # Форматируем дату из start_time с защитой от None
            if exchange.start_time:
                date_str = exchange.start_time.strftime("%d.%m.%Y")
            else:
                date_str = "Не указано"

            available_exchanges.append({
                "id": exchange.id,
                "time": time_str,
                "date": date_str,
                "price": exchange.price,
                "seller_id": exchange.seller_id,
            })

        # Формируем текст активных фильтров (показываем ВСЕ активные фильтры)
        filter_text_parts = []

        # Фильтр по дням - показываем текущее значение
        if day_filter_value == "all":
            filter_text_parts.append("Период: 📅 Все дни")
        elif day_filter_value == "today":
            filter_text_parts.append("Период: 📅 Только сегодня")
        elif day_filter_value == "tomorrow":
            filter_text_parts.append("Период: 📅 Только завтра")
        elif day_filter_value == "current_week":
            filter_text_parts.append("Период: 📅 Только эта неделя")
        elif day_filter_value == "current_month":
            filter_text_parts.append("Период: 📅 Только этот месяц")

        # Фильтр по сменам - показываем текущее значение
        if shift_filter_value == "all":
            filter_text_parts.append("Смена: ⭐ Все")
        elif shift_filter_value == "no_shift":
            filter_text_parts.append("Смена: 🌙 Без смены")
        elif shift_filter_value == "shift":
            filter_text_parts.append("Смена: ☀️ Со сменой")

        filters_text = "\n".join(filter_text_parts) if filter_text_parts else ""

        # Формируем текст активной сортировки
        sorting_text_parts = []

        # Показываем сортировку по дате всегда (это основной критерий)
        if date_sort_value == "nearest":
            sorting_text_parts.append("По дате: 📈 Сначала ближайшие")
        else:
            sorting_text_parts.append("По дате: 📉 Сначала дальние")

        # Показываем сортировку по цене всегда (вторичный критерий)
        if price_sort_value == "cheap":
            sorting_text_parts.append("По цене: 💰 Сначала дешевые")
        else:
            sorting_text_parts.append("По цене: 💸 Сначала дорогие")

        sorting_text = "\n".join(sorting_text_parts)

        # Определяем, отличаются ли настройки от значений по умолчанию
        is_default_settings = (
            day_filter_value == "all"
            and shift_filter_value == "all"
            and date_sort_value == "nearest"
            and price_sort_value == "cheap"
        )

        return {
            "available_exchanges": available_exchanges,
            "exchanges_length": len(available_exchanges),
            "has_exchanges": len(available_exchanges) > 0,
            "active_filters": filters_text,
            "has_active_filters": True,  # Всегда показываем фильтры
            "active_sorting": sorting_text,
            "has_active_sorting": True,  # Всегда показываем сортировку
            "show_reset_button": not is_default_settings,
        }

    except Exception:
        return {
            "available_exchanges": [],
            "has_exchanges": False,
            "active_filters": "Период: 📅 Все дни\nСмена: ⭐ Все",
            "has_active_filters": True,
            "active_sorting": "По дате: 📈 Сначала ближайшие\nПо цене: 💰 Сначала дешевые",
            "has_active_sorting": True,
            "show_reset_button": False,
        }


async def exchange_sell_getter(
    stp_repo: MainRequestsRepo, user: Employee, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна продажи часов.

    Показывает предложения покупок (то, что другие хотят купить и мы можем продать).

    Args:
        stp_repo: Репозиторий операций с базой STP
        user: Экземпляр пользователя с моделью Employee
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с доступными сделками
    """
    user_id = dialog_manager.event.from_user.id

    try:
        # Получаем сделки покупок (то, что другие хотят купить и мы можем продать)
        buy_requests = await stp_repo.exchange.get_active_exchanges(
            exclude_user_id=user_id,
            division="НЦК" if user.division == "НЦК" else ["НТП1", "НТП2"],
            exchange_type="buy",
        )

        # Форматируем данные для отображения
        available_buy_requests = []
        for exchange in buy_requests:
            # Форматируем время из start_time и end_time с защитой от None
            if exchange.start_time and exchange.end_time:
                time_str = f"{exchange.start_time.strftime('%H:%M')}-{exchange.end_time.strftime('%H:%M')}"
            elif exchange.start_time:
                time_str = f"{exchange.start_time.strftime('%H:%M')}-Не указано"
            else:
                time_str = "Не указано"

            # Форматируем дату из start_time с защитой от None
            if exchange.start_time:
                date_str = exchange.start_time.strftime("%d.%m.%Y")
            else:
                date_str = "Не указано"

            available_buy_requests.append({
                "id": exchange.id,
                "time": time_str,
                "date": date_str,
                "price": exchange.price,
                "buyer_id": exchange.seller_id,  # В buy-запросе seller_id это фактически buyer_id
            })

        return {
            "available_buy_requests": available_buy_requests,
            "buy_requests_length": len(available_buy_requests),
            "has_buy_requests": len(available_buy_requests) > 0,
        }

    except Exception:
        return {
            "available_buy_requests": [],
            "has_buy_requests": False,
        }


async def exchange_buy_detail_getter(
    user: Employee, stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **kwargs
) -> Dict[str, Any]:
    """Геттер для детального просмотра обмена при покупке."""
    exchange_id = (
        dialog_manager.dialog_data.get("exchange_id", None)
        or dialog_manager.start_data["exchange_id"]
    )

    if not exchange_id:
        return {"error": "Обмен не найден"}

    try:
        # Получаем детали обмена
        exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
        if not exchange:
            return {"error": "Обмен не найден"}

        # Получаем информацию о продавце
        seller = await stp_repo.employee.get_users(user_id=exchange.seller_id)

        # Информация об оплате
        if exchange.payment_type == "immediate":
            payment_info = "Сразу при покупке"
        elif exchange.payment_date:
            payment_info = f"До {exchange.payment_date.strftime('%d.%m.%Y')}"
        else:
            payment_info = "По договоренности"

        exchange_info = await get_exchange_text(stp_repo, exchange, user.user_id)
        deeplink = f"exchange_{exchange.id}"
        comment = exchange.comment

        # Проверяем дежурства продавца на дату смены
        duty_warning = ""
        try:
            date_obj = exchange.start_time.date()
            duty_parser = DutyScheduleParser()
            duties_for_date = await duty_parser.get_duties_for_date(
                date_obj, seller.division, stp_repo
            )

            if duties_for_date:
                # Проверяем, есть ли продавец среди дежурных
                for duty in duties_for_date:
                    if duty_parser.names_match(seller.fullname, duty.name):
                        duty_warning = f"🚩 <b>Включает дежурство:</b>\n{duty.schedule} {duty.shift_type}"
                        break
        except Exception as e:
            logger.debug(f"[Биржа] Ошибка проверки дежурств продавца: {e}")

        result = {
            "exchange_info": exchange_info,
            "payment_info": payment_info,
            "comment": comment,
            "deeplink": deeplink,
        }

        # Добавляем информацию о дежурстве если есть
        if duty_warning:
            result["duty_warning"] = duty_warning

        return result

    except Exception:
        return {"error": "Ошибка загрузки данных"}


async def exchange_sell_detail_getter(
    user: Employee, stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **kwargs
) -> Dict[str, Any]:
    """Геттер для детального просмотра запроса на покупку (buy request)."""
    exchange_id = (
        dialog_manager.dialog_data.get("exchange_id", None)
        or dialog_manager.start_data["exchange_id"]
    )

    if not exchange_id:
        return {"error": "Запрос не найден"}

    try:
        # Получаем детали обмена
        exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
        if not exchange:
            return {"error": "Запрос не найден"}

        # Проверяем, что это buy-запрос
        if exchange.type != "buy":
            return {"error": "Неверный тип запроса"}

        # Информация об оплате
        if exchange.payment_type == "immediate":
            payment_info = "Сразу при продаже"
        elif exchange.payment_date:
            payment_info = f"До {exchange.payment_date.strftime('%d.%m.%Y')}"
        else:
            payment_info = "По договоренности"

        exchange_info = await get_exchange_text(stp_repo, exchange, user.user_id)
        deeplink = f"buy_request_{exchange.id}"

        return {
            "exchange_info": exchange_info,
            "payment_info": payment_info,
            "deeplink": deeplink,
        }

    except Exception as e:
        logger.error(f"[Биржа] Ошибка при просмотре сделки: {e}")
        return {"error": "Ошибка загрузки данных"}


async def my_exchanges(
    stp_repo: MainRequestsRepo, user: Employee, dialog_manager: DialogManager, **kwargs
) -> Dict[str, Any]:
    """Геттер для отображения всех обменов пользователя."""
    user_id = dialog_manager.event.from_user.id

    try:
        # Получаем все обмены пользователя (как продажи, так и покупки)
        exchanges = await stp_repo.exchange.get_user_exchanges(
            user_id=user_id,
            exchange_type="all",  # Получаем все типы обменов
        )

        # Форматируем данные для отображения
        my_exchanges_list = []
        for exchange in exchanges:
            # Форматируем дату из start_time с защитой от None
            if exchange.start_time:
                date_str = exchange.start_time.strftime("%d.%m")
            else:
                date_str = "Не указано"

            # Определяем тип и статус обмена для пользователя
            if exchange.seller_id == user_id:
                # Пользователь - продавец или создатель запроса на покупку
                if exchange.type == "sell":
                    # Пользователь продает смену
                    if exchange.status == "sold":
                        button_text = f"📉 Продал {date_str}"
                    elif exchange.status == "active":
                        button_text = f"📉 Продаю {date_str}"
                    else:  # cancelled, expired, inactive
                        button_text = f"Отменил {date_str}"
                else:  # exchange.type == "buy"
                    # Пользователь создал запрос на покупку
                    if exchange.status == "sold":
                        button_text = f"📈 Купил {date_str}"
                    elif exchange.status == "active":
                        button_text = f"📈 Покупаю {date_str}"
                    else:  # cancelled, expired, inactive
                        button_text = f"Отменил {date_str}"
            else:
                # Пользователь - покупатель (buyer_id == user_id)
                if exchange.type == "sell":
                    # Пользователь купил чужое предложение продажи
                    button_text = f"📈 Купил {date_str}"
                else:
                    # Пользователь принял чужой запрос на покупку (продал)
                    button_text = f"📉 Продал {date_str}"

            my_exchanges_list.append({
                "id": exchange.id,
                "button_text": button_text,
                "type": exchange.type,
                "status": exchange.status,
                "is_seller": exchange.seller_id == user_id,
                "date": date_str,
                "time": f"{exchange.start_time.strftime('%H:%M') if exchange.start_time else 'Не указано'}-{exchange.end_time.strftime('%H:%M') if exchange.end_time else 'Не указано'}".rstrip(
                    "-"
                ),
                "price": exchange.price,
            })

        return {
            "my_exchanges": my_exchanges_list,
            "length": len(my_exchanges_list),
            "has_exchanges": len(my_exchanges_list) > 0,
        }

    except Exception:
        return {
            "my_exchanges": [],
            "has_exchanges": False,
        }


async def _get_other_party_info(
    exchange: Exchange, user_id: int, stp_repo: MainRequestsRepo
) -> tuple[str | None, str | None]:
    """Get information about the other party in the exchange."""
    if user_id and exchange.seller_id == user_id:
        other_party_id = exchange.buyer_id
        other_party_type = "Покупатель"
    else:
        other_party_id = exchange.seller_id
        other_party_type = "Продавец"

    if not other_party_id:
        return None, None

    try:
        other_party_user = await stp_repo.employee.get_users(user_id=other_party_id)
        if other_party_user:
            other_party_name = format_fullname(
                other_party_user.fullname,
                short=True,
                gender_emoji=True,
                username=other_party_user.username,
                user_id=other_party_user.user_id,
            )
            return other_party_name, other_party_type
    except Exception as e:
        logger.error(f"[Биржа] Ошибка получения информации о другой стороне: {e}")

    return None, None


async def my_detail_getter(
    user: Employee,
    bot: Bot,
    stp_repo: MainRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> Dict[str, Any]:
    """Геттер для детального просмотра собственного обмена."""
    exchange_id = (
        dialog_manager.dialog_data.get("exchange_id", None)
        or dialog_manager.start_data["exchange_id"]
    )

    exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
    is_seller = exchange.seller_id == dialog_manager.event.from_user.id

    # Установка чекбоксов
    in_schedule: ManagedCheckbox = dialog_manager.find(
        "exchange_in_schedule"
    )  # В графике
    await in_schedule.set_checked(
        exchange.in_seller_schedule if is_seller else exchange.in_buyer_schedule
    )

    exchange_is_paid: ManagedCheckbox = dialog_manager.find(
        "exchange_is_paid"
    )  # Статус оплаты
    await exchange_is_paid.set_checked(exchange.is_paid)

    private_checkbox: ManagedCheckbox = dialog_manager.find(
        "offer_private_status"
    )  # Статус приватности
    await private_checkbox.set_checked(exchange.is_private)

    # Статус сделки
    exchange_status = dialog_manager.find("offer_status")
    if exchange_status:
        await exchange_status.set_checked(exchange.status == "active")

    # Get other party information
    other_party_name, other_party_type = await _get_other_party_info(
        exchange, user.user_id, stp_repo
    )

    exchange_text = await get_exchange_text(stp_repo, exchange, user.user_id)
    exchange_status = await get_exchange_status(exchange)
    exchange_type = await get_exchange_type(exchange, is_seller=is_seller)

    # Generate deeplink
    exchange_deeplink = f"exchange_{exchange.id}"
    exchange_deeplink_url = await create_start_link(
        bot=bot, payload=exchange_deeplink, encode=True
    )

    # Check if exchange can be reactivated
    could_activate = exchange.status in [
        "inactive",
        "canceled",
        "expired",
    ] and tz.localize(exchange.start_time) > datetime.now(tz=tz)

    return {
        "exchange_info": exchange_text,
        "comment": exchange.comment,
        "status": exchange.status,
        "status_text": exchange_status,
        "other_party_name": other_party_name,
        "other_party_type": other_party_type,
        "has_other_party": bool(other_party_name),
        "is_active": exchange.status == "active",
        "exchange_type": exchange_type,
        "created_date": exchange.created_at.strftime(strftime_date)
        if exchange.created_at
        else "Не указано",
        "is_paid": "Да" if exchange.is_paid else "Нет",
        "deeplink": exchange_deeplink,
        "deeplink_url": exchange_deeplink_url,
        "could_activate": could_activate,
        "is_seller": is_seller,
    }


async def edit_offer_date_getter(
    stp_repo: MainRequestsRepo, user: Employee, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна выбора даты."""
    # Подготавливаем данные календаря с информацией о сменах
    await prepare_calendar_data_for_exchange(stp_repo, user, dialog_manager)
    return {}

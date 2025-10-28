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
from tgbot.misc.helpers import format_fullname, tz
from tgbot.services.files_processing.parsers.schedule import ScheduleParser

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


async def get_exchange_text(exchange: Exchange, user_id: int) -> str:
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
    shift_date = exchange.start_time.strftime("%d.%m.%Y")
    shift_time = (
        f"{exchange.start_time.strftime('%H:%M')}-{exchange.end_time.strftime('%H:%M')}"
    )
    shift_hours = await get_exchange_hours(exchange)
    price = exchange.price

    if exchange.type == "sell":
        price_per_hour = await get_exchange_price_per_hour(exchange)
        exchange_text = f"""<blockquote><b>{exchange_type}:</b>
<code>{shift_time} ({shift_hours:g} ч.) {shift_date} ПРМ</code>
💰 <b>Цена:</b>
<code>{price:g} р. ({price_per_hour:g} р./ч.)</code></blockquote>"""
    else:
        exchange_text = f"""<blockquote><b>{exchange_type}:</b>
<code>{shift_time} ({shift_hours:g} ч.) {shift_date} ПРМ</code>
💰 <b>Цена:</b>
<code>{price:g} р./ч.</code></blockquote>"""
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
    user_id = dialog_manager.event.from_user.id

    try:
        # Получаем сделки продаж (то, что другие продают и мы можем купить)
        exchanges = await stp_repo.exchange.get_active_exchanges(
            exclude_user_id=user_id,
            division="НЦК" if user.division == "НЦК" else ["НТП1", "НТП2"],
            exchange_type="sell",
        )

        # Форматируем данные для отображения
        available_exchanges = []
        for exchange in exchanges:
            # Форматируем время из start_time и end_time
            time_str = f"{exchange.start_time.strftime('%H:%M')}-{exchange.end_time.strftime('%H:%M')}"

            # Форматируем дату из start_time
            date_str = exchange.start_time.strftime("%d.%m.%Y")

            available_exchanges.append({
                "id": exchange.id,
                "time": time_str,
                "date": date_str,
                "price": exchange.price,
                "seller_id": exchange.seller_id,
            })

        return {
            "available_exchanges": available_exchanges,
            "exchanges_length": len(available_exchanges),
            "has_exchanges": len(available_exchanges) > 0,
        }

    except Exception:
        return {
            "available_exchanges": [],
            "has_exchanges": False,
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
            # Форматируем время из start_time и end_time
            time_str = f"{exchange.start_time.strftime('%H:%M')}-{exchange.end_time.strftime('%H:%M')}"

            # Форматируем дату из start_time
            date_str = exchange.start_time.strftime("%d.%m.%Y")

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
    if dialog_manager.start_data:
        exchange_id = dialog_manager.start_data.get("exchange_id", None)
    else:
        exchange_id = dialog_manager.dialog_data.get("exchange_id", None)

    if not exchange_id:
        return {"error": "Обмен не найден"}

    try:
        # Получаем детали обмена
        exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
        if not exchange:
            return {"error": "Обмен не найден"}

        # Получаем информацию о продавце
        seller = await stp_repo.employee.get_users(user_id=exchange.seller_id)
        seller_name = format_fullname(
            seller.fullname,
            short=True,
            gender_emoji=True,
            username=seller.username,
            user_id=seller.user_id,
        )

        # Информация об оплате
        if exchange.payment_type == "immediate":
            payment_info = "Сразу при покупке"
        elif exchange.payment_date:
            payment_info = f"До {exchange.payment_date.strftime('%d.%m.%Y')}"
        else:
            payment_info = "По договоренности"

        exchange_info = await get_exchange_text(exchange, user.user_id)
        deeplink = f"exchange_{exchange.id}"
        comment = exchange.comment

        return {
            "exchange_info": exchange_info,
            "seller_name": seller_name,
            "payment_info": payment_info,
            "comment": comment,
            "deeplink": deeplink,
        }

    except Exception:
        return {"error": "Ошибка загрузки данных"}


async def exchange_sell_detail_getter(
    user: Employee, stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **kwargs
) -> Dict[str, Any]:
    """Геттер для детального просмотра запроса на покупку (buy request)."""
    if dialog_manager.start_data:
        exchange_id = dialog_manager.start_data.get("exchange_id", None)
    else:
        exchange_id = dialog_manager.dialog_data.get("exchange_id", None)

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

        # Получаем информацию о покупателе (в buy-запросе seller_id это фактически buyer_id)
        buyer = await stp_repo.employee.get_users(user_id=exchange.seller_id)
        buyer_name = format_fullname(
            buyer.fullname,
            short=True,
            gender_emoji=True,
            username=buyer.username,
            user_id=buyer.user_id,
        )

        # Информация об оплате
        if exchange.payment_type == "immediate":
            payment_info = "Сразу при продаже"
        elif exchange.payment_date:
            payment_info = f"До {exchange.payment_date.strftime('%d.%m.%Y')}"
        else:
            payment_info = "По договоренности"

        exchange_info = await get_exchange_text(exchange, user.user_id)
        deeplink = f"buy_request_{exchange.id}"

        return {
            "exchange_info": exchange_info,
            "buyer_name": buyer_name,
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
            # Форматируем дату из start_time
            date_str = exchange.start_time.strftime("%d.%m")

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
                "time": f"{exchange.start_time.strftime('%H:%M')}-{exchange.end_time.strftime('%H:%M') if exchange.end_time else ''}".rstrip(
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


async def _safely_set_checkbox(
    checkbox: ManagedCheckbox, value: bool, checkbox_name: str
) -> None:
    """Safely set checkbox value with error handling."""
    if checkbox:
        try:
            await checkbox.set_checked(value)
        except AttributeError as e:
            if "'NoneType' object has no attribute 'user_id'" in str(e):
                logger.warning(
                    f"[Биржа] Пропуск установки {checkbox_name} из-за проблемы контекста: {e}"
                )
            else:
                raise


async def _get_payment_info(exchange: Exchange) -> str:
    """Get formatted payment information for exchange."""
    if exchange.payment_type == "immediate":
        return "Сразу при проведении сделки"
    elif exchange.payment_date:
        return f"До {exchange.payment_date.strftime('%d.%m.%Y')}"
    else:
        return "По договоренности"


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


async def _setup_exchange_checkboxes(
    exchange: Exchange, user: Employee, dialog_manager: DialogManager
) -> None:
    """Setup all exchange-related checkboxes."""
    # In schedule checkbox
    in_schedule_checkbox = dialog_manager.find("exchange_in_schedule")
    if in_schedule_checkbox and user.user_id is not None:
        if exchange.seller_id == user.user_id:
            await _safely_set_checkbox(
                in_schedule_checkbox,
                exchange.in_seller_schedule,
                "exchange_in_schedule",
            )
        else:
            await _safely_set_checkbox(
                in_schedule_checkbox, exchange.in_buyer_schedule, "exchange_in_schedule"
            )

    # Payment status checkbox
    exchange_is_paid = dialog_manager.find("exchange_is_paid")
    if exchange_is_paid:
        await exchange_is_paid.set_checked(exchange.is_paid)

    # Private status checkbox
    private_checkbox = dialog_manager.find("offer_private_status")
    await _safely_set_checkbox(
        private_checkbox, exchange.is_private, "offer_private_status"
    )

    # Статус сделки
    exchange_status = dialog_manager.find("offer_status")
    if exchange_status:
        await exchange_status.set_checked(exchange.status == "active")


async def my_detail_getter(
    user: Employee,
    bot: Bot,
    stp_repo: MainRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> Dict[str, Any]:
    """Геттер для детального просмотра собственного обмена."""
    # Get exchange ID from dialog data
    if dialog_manager.start_data:
        exchange_id = dialog_manager.start_data.get("exchange_id")
    else:
        exchange_id = dialog_manager.dialog_data.get("exchange_id")

    if not exchange_id:
        return {"error": "Обмен не найден"}

    if not user.user_id:
        return {"error": "Пользователь не найден"}

    try:
        # Get exchange details
        exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
        if not exchange:
            return {"error": "Обмен не найден"}

        # Setup UI checkboxes
        await _setup_exchange_checkboxes(exchange, user, dialog_manager)

        # Get payment information
        payment_info = await _get_payment_info(exchange)

        # Get other party information
        other_party_name, other_party_type = await _get_other_party_info(
            exchange, user.user_id, stp_repo
        )

        # Determine user role and prepare exchange info
        is_seller = user.user_id and exchange.seller_id == user.user_id
        exchange_text = await get_exchange_text(exchange, user.user_id or 0)
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
            "payment_info": payment_info,
            "comment": exchange.comment,
            "status": exchange.status,
            "status_text": exchange_status,
            "other_party_name": other_party_name,
            "other_party_type": other_party_type,
            "has_other_party": bool(other_party_name),
            "is_active": exchange.status == "active",
            "exchange_type": exchange_type,
            "created_date": exchange.created_at.strftime("%d.%m.%Y %H:%M"),
            "is_paid": "Да" if exchange.is_paid else "Нет",
            "deeplink": exchange_deeplink,
            "deeplink_url": exchange_deeplink_url,
            "could_activate": could_activate,
            "is_seller": is_seller,
        }

    except Exception as e:
        logger.error(f"[Биржа] Ошибка при просмотре своей сделки: {e}")
        return {"error": "Ошибка загрузки данных"}


async def edit_offer_date_getter(
    stp_repo: MainRequestsRepo, user: Employee, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна выбора даты."""
    # Подготавливаем данные календаря с информацией о сменах
    await prepare_calendar_data_for_exchange(stp_repo, user, dialog_manager)
    return {}

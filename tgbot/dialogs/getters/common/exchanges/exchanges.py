"""Геттеры для биржи подмен."""

import re
from datetime import datetime
from typing import Any, Dict

from aiogram import Bot
from aiogram.utils.deep_linking import create_start_link
from aiogram_dialog import DialogManager
from stp_database import Employee, MainRequestsRepo

from tgbot.misc.helpers import format_fullname
from tgbot.services.files_processing.parsers.schedule import ScheduleParser


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

            # Определяем пол пользователя для правильного эмодзи
            gender = determine_user_gender(user.fullname)
            dialog_manager.dialog_data["user_gender"] = gender

        except Exception:
            # В случае ошибки просто не показываем смены
            dialog_manager.dialog_data["shift_dates"] = {}

    except Exception:
        # В случае ошибки просто не показываем смены
        dialog_manager.dialog_data["shift_dates"] = {}


def determine_user_gender(fullname: str) -> str:
    """Определяет пол пользователя на основе имени."""
    if not fullname:
        return "unknown"

    # Простая эвристика на основе окончаний имен
    name_parts = fullname.split()
    if len(name_parts) >= 2:
        first_name = name_parts[1].lower()  # Второе слово обычно имя

        # Мужские окончания
        male_endings = ["ич", "ев", "ов", "ин", "ан", "ён", "он", "ий", "ей", "ай"]
        # Женские окончания
        female_endings = [
            "на",
            "ра",
            "ла",
            "да",
            "га",
            "ка",
            "са",
            "та",
            "ва",
            "ья",
            "ия",
            "ая",
        ]

        for ending in female_endings:
            if first_name.endswith(ending):
                return "female"

        for ending in male_endings:
            if first_name.endswith(ending):
                return "male"

    return "unknown"


async def exchange_buy_getter(
    stp_repo: MainRequestsRepo, user: Employee, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для окна покупки обменов.

    Показывает sell-предложения (то, что мы можем купить).
    """
    user_id = dialog_manager.event.from_user.id

    try:
        # Получаем sell-предложения (то, что другие продают и мы можем купить)
        exchanges = await stp_repo.exchange.get_active_exchanges(
            exclude_user_id=user_id,
            division="НЦК" if user.division == "НЦК" else ["НТП1", "НТП2"],
            exchange_type="sell",
        )

        # Форматируем данные для отображения
        available_exchanges = []
        for exchange in exchanges:
            # Форматируем время из start_time и end_time
            if exchange.end_time:
                time_str = f"{exchange.start_time.strftime('%H:%M')}-{exchange.end_time.strftime('%H:%M')}"
            else:
                time_str = f"с {exchange.start_time.strftime('%H:%M')} (полная смена)"

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
    """Геттер для окна продажи обменов.

    Показывает buy-запросы (то, что другие хотят купить и мы можем продать).
    """
    user_id = dialog_manager.event.from_user.id

    try:
        # Получаем buy-запросы (то, что другие хотят купить и мы можем продать)
        buy_requests = await stp_repo.exchange.get_active_exchanges(
            exclude_user_id=user_id,
            division="НЦК" if user.division == "НЦК" else ["НТП1", "НТП2"],
            exchange_type="buy",
        )

        # Форматируем данные для отображения
        available_buy_requests = []
        for exchange in buy_requests:
            # Форматируем время из start_time и end_time
            if exchange.end_time:
                time_str = f"{exchange.start_time.strftime('%H:%M')}-{exchange.end_time.strftime('%H:%M')}"
            else:
                time_str = f"с {exchange.start_time.strftime('%H:%M')} (полная смена)"

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
    stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **kwargs
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

        # Форматируем данные
        shift_date = exchange.start_time.strftime("%d.%m.%Y")

        if exchange.end_time:
            shift_time = f"{exchange.start_time.strftime('%H:%M')}-{exchange.end_time.strftime('%H:%M')}"
        else:
            shift_time = f"с {exchange.start_time.strftime('%H:%M')} (полная смена)"

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

        # Информация об оплате
        if exchange.payment_type == "immediate":
            payment_info = "Сразу при покупке"
        elif exchange.payment_date:
            payment_info = f"До {exchange.payment_date.strftime('%d.%m.%Y')}"
        else:
            payment_info = "По договоренности"

        deeplink = f"exchange_{exchange.id}"
        comment = exchange.comment

        return {
            "shift_date": shift_date,
            "seller_name": seller_name,
            "shift_time": shift_time,
            "price": exchange.price,
            "price_per_hour": price_per_hour,
            "payment_info": payment_info,
            "comment": comment,
            "deeplink": deeplink,
        }

    except Exception:
        return {"error": "Ошибка загрузки данных"}


async def exchange_sell_detail_getter(
    stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **kwargs
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

        # Форматируем данные
        shift_date = exchange.start_time.strftime("%d.%m.%Y")
        if exchange.end_time:
            shift_time = f"{exchange.start_time.strftime('%H:%M')}-{exchange.end_time.strftime('%H:%M')}"
        else:
            shift_time = f"с {exchange.start_time.strftime('%H:%M')} (полная смена)"

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

        # Информация об оплате
        if exchange.payment_type == "immediate":
            payment_info = "Сразу при продаже"
        elif exchange.payment_date:
            payment_info = f"До {exchange.payment_date.strftime('%d.%m.%Y')}"
        else:
            payment_info = "По договоренности"

        deeplink = f"buy_request_{exchange.id}"

        return {
            "shift_date": shift_date,
            "shift_time": shift_time,
            "price": exchange.price,
            "price_per_hour": price_per_hour,
            "buyer_name": buyer_name,
            "payment_info": payment_info,
            "deeplink": deeplink,
        }

    except Exception:
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


async def my_detail_getter(
    bot: Bot, stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **kwargs
) -> Dict[str, Any]:
    """Геттер для детального просмотра собственного обмена."""
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

        user_id = dialog_manager.event.from_user.id

        # Форматируем данные
        shift_date = exchange.start_time.strftime("%d.%m.%Y")
        if exchange.end_time:
            shift_time = f"{exchange.start_time.strftime('%H:%M')}-{exchange.end_time.strftime('%H:%M')}"
        else:
            shift_time = f"с {exchange.start_time.strftime('%H:%M')} (полная смена)"

        # Рассчитываем количество часов смены и цену за час
        shift_hours = 0
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

        # Информация об оплате
        if exchange.payment_type == "immediate":
            payment_info = "Сразу при проведении сделки"
        elif exchange.payment_date:
            payment_info = f"До {exchange.payment_date.strftime('%d.%m.%Y')}"
        else:
            payment_info = "По договоренности"

        # Определяем контекст и роль пользователя
        is_seller = exchange.seller_id == user_id
        other_party = None
        status_text = ""

        if exchange.status == "active":
            if exchange.type == "sell":
                status_text = "🟢 Активное предложение продажи"
            else:  # buy
                status_text = "🟢 Активный запрос на покупку"
        elif exchange.status == "sold":
            # Получаем информацию о второй стороне сделки
            if is_seller and exchange.buyer_id:
                other_party = await stp_repo.employee.get_users(
                    user_id=exchange.buyer_id
                )
                if exchange.type == "sell":
                    status_text = "✅ Смена продана"
                else:  # buy
                    status_text = "✅ Смена куплена"
            elif not is_seller and exchange.seller_id:
                other_party = await stp_repo.employee.get_users(
                    user_id=exchange.seller_id
                )
                if exchange.type == "sell":
                    status_text = "✅ Смена куплена"
                else:  # buy
                    status_text = "✅ Смена продана"
        elif exchange.status in ["canceled", "expired"]:
            if exchange.status == "canceled":
                status_text = "❌ Отменено"
            else:
                status_text = "⏰ Истекло"
        else:
            status_text = f"ℹ️ {exchange.status.title()}"

        # Форматируем имя второй стороны
        other_party_name = ""
        if other_party:
            other_party_name = format_fullname(
                other_party.fullname,
                short=True,
                gender_emoji=True,
                username=other_party.username,
                user_id=other_party.user_id,
            )

        # Определяем тип операции для заголовка
        if exchange.type == "sell":
            if is_seller:
                operation_type = "Продам"
            else:
                operation_type = "Куплю"
        else:  # buy
            if is_seller:  # Создатель buy-запроса
                operation_type = "запрос на покупку"
            else:  # Тот кто принял buy-запрос
                operation_type = "Продам"

        deeplink = f"exchange_{exchange.id}"
        deeplink_url = await create_start_link(bot=bot, payload=deeplink, encode=True)

        return {
            "shift_date": shift_date,
            "shift_time": shift_time,
            "price": exchange.price,
            "price_per_hour": price_per_hour,
            "payment_info": payment_info,
            "comment": exchange.comment or "Без комментария",
            "status_text": status_text,
            "operation_type": operation_type,
            "other_party_name": other_party_name,
            "has_other_party": bool(other_party_name),
            "is_active": exchange.status == "active",
            "is_seller": is_seller,
            "exchange_type": exchange.type,
            "created_date": exchange.created_at.strftime("%d.%m.%Y %H:%M"),
            "is_paid": exchange.is_paid,
            "deeplink": deeplink,
            "deeplink_url": deeplink_url,
        }

    except Exception:
        return {"error": "Ошибка загрузки данных"}

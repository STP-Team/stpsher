"""Геттеры для биржи подмен."""

import logging
import re
from datetime import datetime
from typing import Any, Dict

from aiogram import Bot
from aiogram.utils.deep_linking import create_start_link
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import ManagedCheckbox, ManagedRadio
from stp_database import Employee, Exchange, MainRequestsRepo

from tgbot.misc.dicts import exchange_emojis
from tgbot.misc.helpers import (
    format_currency_price,
    format_fullname,
    strftime_date,
    tz_moscow,
    tz_perm,
)
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
    """Подготавливает данные календаря ТОЛЬКО для текущего отображаемого месяца."""
    try:
        # Получаем календарный виджет и определяем отображаемый месяц
        calendar_widget = (
            dialog_manager.find("sell_date_calendar")
            or dialog_manager.find("buy_date_calendar")
            or dialog_manager.find("subscription_dates")
        )

        # Определяем месяц для загрузки
        if calendar_widget:
            current_offset = calendar_widget.get_offset()
        else:
            current_offset = None

        # Используем отображаемый месяц или текущий как fallback
        if current_offset is None:
            current_offset = datetime.now().date()

        displayed_month = current_offset.month
        displayed_year = current_offset.year

        # Проверяем, не загружали ли мы уже данные для этого месяца
        loaded_month = dialog_manager.dialog_data.get("loaded_month", "")
        current_month_key = f"{displayed_month:02d}/{displayed_year}"

        if loaded_month == current_month_key:
            # Данные уже загружены для этого месяца
            logger.debug(
                f"[Биржа] Данные для {get_month_name(displayed_month)} {displayed_year} уже загружены"
            )
            return

        month_name = get_month_name(displayed_month)
        logger.debug(
            f"[Биржа] Загружаем данные календаря для {month_name} {displayed_year}"
        )

        # Загружаем данные ТОЛЬКО для отображаемого месяца
        parser = ScheduleParser()
        all_shift_dates = {}
        current_date = datetime.now().date()

        try:
            # Парсер расписания работает только с текущим годом
            if displayed_year > current_date.year:
                logger.debug(
                    f"[Биржа] Пропускаем {month_name} {displayed_year} - парсер работает только с текущим годом"
                )
                dialog_manager.dialog_data["shift_dates"] = {}
                dialog_manager.dialog_data["loaded_month"] = current_month_key
                return

            # Проверяем, есть ли этот месяц в файле расписания
            try:
                base_schedule = parser.get_user_schedule(
                    user.fullname, month_name, user.division
                )
                logger.info(
                    f"[Биржа] {month_name} {displayed_year}: Найдено {len(base_schedule)} дней в базовом расписании"
                )
            except Exception as e:
                logger.warning(
                    f"[Биржа] {month_name} {displayed_year}: Ошибка получения базового расписания: {e}"
                )
                # Если базовое расписание не найдено, пропускаем этот месяц
                dialog_manager.dialog_data["shift_dates"] = {}
                dialog_manager.dialog_data["loaded_month"] = current_month_key
                return

            schedule_dict = await parser.get_user_schedule_with_duties(
                user.fullname,
                month_name,
                user.division,
                stp_repo,
                current_day_only=False,
            )

            # Проверяем, что получили данные
            if not schedule_dict:
                logger.debug(
                    f"[Биржа] Нет данных расписания для {month_name} {displayed_year}"
                )
                dialog_manager.dialog_data["shift_dates"] = {}
                dialog_manager.dialog_data["loaded_month"] = current_month_key
                return

            # Извлекаем рабочие дни для отладки
            work_days = []
            for day, (schedule, duty_info) in schedule_dict.items():
                if schedule and schedule not in ["Не указано", "В", "О"]:
                    day_match = re.search(r"(\d{1,2})", day)
                    if day_match:
                        work_days.append(int(day_match.group(1)))

            # Извлекаем дни когда есть смены
            for day, (schedule, duty_info) in schedule_dict.items():
                if schedule and schedule not in ["Не указано", "В", "О"]:
                    # Извлекаем номер дня
                    day_match = re.search(r"(\d{1,2})", day)
                    if day_match:
                        day_num = f"{int(day_match.group(1)):02d}"
                        # Создаем уникальный ключ для месяца и дня
                        month_day_key = f"{displayed_month:02d}_{day_num}"
                        all_shift_dates[month_day_key] = {
                            "schedule": schedule,
                            "duty_info": duty_info,
                            "month": displayed_month,
                            "day": int(day_num),
                            "year": displayed_year,
                        }
                        # Также сохраняем под простым ключом дня для обратной совместимости с текущим месяцем
                        if (
                            displayed_month == current_date.month
                            and displayed_year == current_date.year
                        ):
                            all_shift_dates[day_num] = {
                                "schedule": schedule,
                                "duty_info": duty_info,
                            }

            logger.debug(
                f"[Биржа] Загружено {len(all_shift_dates)} дней для {month_name} {displayed_year}"
            )

        except Exception as e:
            logger.debug(
                f"[Биржа] Ошибка загрузки данных для {month_name} {displayed_year}: {e}"
            )
            all_shift_dates = {}

        # Сохраняем данные в dialog_data для использования в календаре
        dialog_manager.dialog_data["shift_dates"] = all_shift_dates
        dialog_manager.dialog_data["loaded_month"] = current_month_key
        logger.debug(
            f"[Биржа] Сохранено {len(all_shift_dates)} записей календаря для {month_name} {displayed_year}"
        )

    except Exception as e:
        logger.debug(f"[Биржа] Ошибка подготовки данных календаря: {e}")
        # В случае ошибки просто не показываем смены
        dialog_manager.dialog_data["shift_dates"] = {}


async def _get_exchange_shift_time(start_time: str, end_time: str) -> str:
    """Получает время смены для сделки.

    Args:
        start_time: Время начала смены
        end_time: Время конца смены

    Returns:
        Форматированная строка со временем смены сделки
    """
    # Извлекаем только время из datetime строк
    start_time_str = start_time.split("T")[1][:5] if "T" in start_time else start_time
    end_time_str = end_time.split("T")[1][:5] if "T" in end_time else end_time

    shift_time = f"{start_time_str}-{end_time_str}"
    return shift_time


async def _get_exchange_type(exchange: Exchange) -> str:
    """Получает тип сделки.

    Args:
        exchange: Экземпляр сделки с моделью Exchange

    Returns:
        Тип сделки: "📉 Отдам" или "📈 Возьму"
    """
    if exchange.owner_intent == "sell":
        operation_type = "📉 Отдам"
    else:
        operation_type = "📈 Возьму"

    return operation_type


async def _get_other_party_info(
    exchange: Exchange, user_id: int, stp_repo: MainRequestsRepo
) -> tuple[str | None, str | None]:
    """Get information about the other party in the exchange."""
    if user_id and exchange.owner_id == user_id:
        other_party_id = exchange.counterpart_id
        other_party_type = "Покупатель"
    else:
        other_party_id = exchange.owner_id
        other_party_type = "Продавец"

    if not other_party_id:
        return None, None

    try:
        other_party_user = await stp_repo.employee.get_users(user_id=other_party_id)
        if other_party_user:
            other_party_name = format_fullname(
                other_party_user,
                short=True,
                gender_emoji=True,
            )
            return other_party_name, other_party_type
    except Exception as e:
        logger.error(f"[Биржа] Ошибка получения информации о другой стороне: {e}")

    return None, None


async def _get_exchange_status(exchange: Exchange) -> str:
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


async def _get_exchange_button_text(
    exchange: Exchange, user_id: int, date_str: str
) -> str:
    """Генерирует текст кнопки для обмена в зависимости от роли пользователя, типа и статуса сделки.

    Args:
        exchange: Экземпляр сделки с моделью Exchange
        user_id: ID текущего пользователя
        date_str: Форматированная дата (например, "15.11")

    Returns:
        Текст кнопки для отображения в списке обменов
    """
    # Определяем роль пользователя в сделке
    is_seller = exchange.owner_id == user_id

    if is_seller:
        # Пользователь - продавец или создатель запроса на покупку
        if exchange.owner_intent == "sell":
            # Пользователь продает смену
            if exchange.status == "sold":
                return f"📉 Продал {date_str}"
            elif exchange.status == "active":
                return f"📉 Продаю {date_str}"
            elif exchange.status == "inactive":
                return f"📉 Приостановил {date_str}"
            elif exchange.status == "canceled":
                return f"📉 Отменил {date_str}"
            elif exchange.status == "expired":
                return f"📉 Просрочил {date_str}"
            else:
                return f"📉 {exchange.status.title()} {date_str}"
        else:  # exchange.owner_intent == "buy"
            # Пользователь создал запрос на покупку
            if exchange.status == "sold":
                return f"📈 Купил {date_str}"
            elif exchange.status == "active":
                return f"📈 Покупаю {date_str}"
            elif exchange.status == "inactive":
                return f"📈 Приостановил {date_str}"
            elif exchange.status == "canceled":
                return f"📈 Отменил {date_str}"
            elif exchange.status == "expired":
                return f"📈 Просрочил {date_str}"
            else:
                return f"📈 {exchange.status.title()} {date_str}"
    else:
        # Пользователь - покупатель (buyer_id == user_id)
        if exchange.owner_intent == "sell":
            # Пользователь купил чужое предложение продажи
            return f"📈 Купил {date_str}"
        else:
            # Пользователь принял чужой запрос на покупку (продал)
            return f"📉 Продал {date_str}"


async def get_exchange_text(
    stp_repo: MainRequestsRepo,
    exchange: Exchange,
    user_id: int,
    use_random_currency: bool = False,
    show_detailed_roles: bool = False,
) -> str:
    """Форматирует текст для отображения информации о сделке.

    Args:
        stp_repo: Репозиторий операций с базой STP
        exchange: Экземпляр сделки с моделью Exchange
        user_id: Идентификатор Telegram
        use_random_currency: Использовать случайную валюту вместо рублей
        show_detailed_roles: Показать детальную информацию о ролях

    Returns:
        Форматированная строка
    """
    # Защита от None значений в датах/времени
    if exchange.start_time:
        shift_date = exchange.start_time.strftime("%d.%m.%Y")
        start_time_str = exchange.start_time.strftime("%H:%M")

        # Правильно конвертируем время в московскую зону
        # Сначала локализуем как пермское время (если нет timezone info), затем конвертируем в московское
        if exchange.start_time.tzinfo is None:
            start_time_perm = tz_perm.localize(exchange.start_time)
        else:
            start_time_perm = exchange.start_time
        start_time_moscow = start_time_perm.astimezone(tz_moscow)
        start_time_moscow_str = start_time_moscow.strftime("%H:%M")
    else:
        shift_date = "Не указано"
        start_time_str = "Не указано"
        start_time_moscow_str = "Не указано"

    if exchange.end_time:
        end_time_str = exchange.end_time.strftime("%H:%M")

        # Правильно конвертируем время в московскую зону
        # Сначала локализуем как пермское время (если нет timezone info), затем конвертируем в московское
        if exchange.end_time.tzinfo is None:
            end_time_perm = tz_perm.localize(exchange.end_time)
        else:
            end_time_perm = exchange.end_time
        end_time_moscow = end_time_perm.astimezone(tz_moscow)
        end_time_moscow_str = end_time_moscow.strftime("%H:%M")
    else:
        end_time_str = "Не указано"
        end_time_moscow_str = "Не указано"

    shift_time = f"{start_time_str}-{end_time_str}"
    shift_time_moscow = f"{start_time_moscow_str}-{end_time_moscow_str}"
    hours_text = (
        f"{exchange.working_hours:g} ч."
        if exchange.working_hours is not None
        else "Не указано"
    )
    price_display = format_currency_price(
        exchange.price, exchange.total_price, use_random_currency
    )

    # Форматируем дату оплаты
    payment_date_str = (
        "сразу"
        if exchange.payment_type == "immediate"
        else (
            exchange.payment_date.strftime("%d.%m.%Y")
            if exchange.payment_date
            else "по договоренности"
        )
    )

    # Формируем блок комментария если он есть
    comment_block = ""
    if exchange.comment:
        comment_block = f"\n💬 <b>Комментарий:</b>\n<blockquote expandable>{exchange.comment}</blockquote>"

    if show_detailed_roles:
        # Детальный режим с указанием ролей
        is_current_user_seller = exchange.owner_id == user_id

        # Получаем информацию о продавце
        seller = await stp_repo.employee.get_users(user_id=exchange.owner_id)
        seller_name = format_fullname(seller, True, True) if seller else "Не указано"

        # Получаем информацию о покупателе (если есть)
        buyer_name = "Не указано"
        if exchange.counterpart_id:
            buyer = await stp_repo.employee.get_users(user_id=exchange.counterpart_id)
            buyer_name = format_fullname(buyer, True, True) if buyer else "Не указано"

        # Определяем роли для отображения в зависимости от типа сделки
        # ВАЖНО: Продавец = тот кто отдает смену и ПЛАТИТ, Покупатель = тот кто берет смену и ПОЛУЧАЕТ оплату
        if exchange.owner_intent == "sell":
            # Для продажи: seller_id - отдает смену и платит, buyer_id - берет смену и получает оплату
            if is_current_user_seller:
                current_user_role = "Продавец (оплата)"
                other_party_role = "Покупатель"
                other_party_name = buyer_name
            else:
                current_user_role = "Покупатель"
                other_party_role = "Продавец (оплата)"
                other_party_name = seller_name
        else:
            # Для запроса покупки: seller_id - хочет взять смену (получить оплату), buyer_id - отдает смену (платит)
            if is_current_user_seller:
                current_user_role = "Покупатель"  # Создатель запроса хочет взять смену
                other_party_role = "Продавец (оплата)"
                other_party_name = buyer_name
            else:
                current_user_role = "Продавец (оплата)"  # Исполнитель отдает смену
                other_party_role = "Покупатель"
                other_party_name = seller_name

        # Определяем тип операции для заголовка
        if exchange.owner_intent == "sell":
            operation_type = "📉 Продажа смены"
        else:
            operation_type = "📈 Покупка смены"

        # Формируем детальную информацию о ролях
        roles_info = f"""👤 <b>Ты:</b> {current_user_role}"""

        if other_party_name != "Не указано":
            roles_info += f"""
🤝 <b>Партнер:</b> {other_party_role} - {other_party_name}"""
        else:
            roles_info += f"""
🤝 <b>Партнер:</b> {other_party_role} - <i>не назначен</i>"""

        exchange_text = f"""<blockquote>{roles_info}

<b>{operation_type}:</b>
<code>{shift_time} ({hours_text}) {shift_date} ПРМ</code>
<code>{shift_time_moscow} МСК</code>
💰 <b>Оплата:</b>
<code>{price_display}</code> - {payment_date_str}{comment_block}</blockquote>"""

    else:
        # Базовый режим
        exchange_type = await _get_exchange_type(exchange)

        # Получаем информацию о пользователе
        if exchange.owner_intent == "sell":
            user_info = await stp_repo.employee.get_users(user_id=exchange.owner_id)
        else:
            user_info = await stp_repo.employee.get_users(user_id=exchange.owner_id)

        user_name = format_fullname(user_info, True, True)

        # Формируем основной текст
        exchange_text = f"""<blockquote>{user_name}

<b>{exchange_type}:</b>
<code>{shift_time} ({hours_text}) {shift_date} ПРМ</code>
<code>{shift_time_moscow} МСК</code>
💰 <b>Оплата:</b>
<code>{price_display}</code> - {payment_date_str}{comment_block}</blockquote>"""

    return exchange_text


async def exchanges_getter(user: Employee, stp_repo: MainRequestsRepo, **_kwargs):
    """Геттер для главного меню подмен.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий для работы с базой данных

    Returns:
        Словарь с информацией о дивизионе и рыночной статистике
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
            owner_intent="sell",
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
            # Определяем направление сортировки для оплаты
            price_multiplier = 1 if price_sort_value == "cheap" else -1

            # Возвращаем кортеж (дата, оплата) с учетом направления сортировки
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
                "owner_id": exchange.owner_id,
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

        # Показываем сортировку по оплате всегда (вторичный критерий)
        if price_sort_value == "cheap":
            sorting_text_parts.append("По оплате: 💰 Сначала дешевые")
        else:
            sorting_text_parts.append("По оплате: 💸 Сначала дорогие")

        sorting_text = "\n".join(sorting_text_parts)

        # Определяем, отличаются ли настройки от значений по умолчанию
        is_default_settings = (
            day_filter_value == "all"
            and shift_filter_value == "all"
            and date_sort_value == "nearest"
            and price_sort_value == "cheap"
        )

        default_filters = day_filter_value == "all" and shift_filter_value == "all"
        default_sorting = date_sort_value == "nearest" and price_sort_value == "cheap"

        return {
            "available_exchanges": available_exchanges,
            "exchanges_length": len(available_exchanges),
            "has_exchanges": len(available_exchanges) > 0,
            "active_filters": filters_text,
            "active_sorting": sorting_text,
            "has_active_filters": not default_filters,
            "has_active_sorting": not default_sorting,
            "show_reset_button": not is_default_settings,
        }

    except Exception:
        return {
            "available_exchanges": [],
            "has_exchanges": False,
            "active_filters": "Период: 📅 Все дни\nСмена: ⭐ Все",
            "active_sorting": "По дате: 📈 Сначала ближайшие\nПо оплате: 💰 Сначала дешевые",
            "has_active_sorting": True,
            "has_active_filters": True,
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
    from datetime import date

    from aiogram_dialog.widgets.kbd import ManagedRadio, ManagedToggle

    user_id = dialog_manager.event.from_user.id

    try:
        # Получаем сделки покупок (то, что другие хотят купить и мы можем продать)
        buy_requests = await stp_repo.exchange.get_active_exchanges(
            exclude_user_id=user_id,
            division="НЦК" if user.division == "НЦК" else ["НТП1", "НТП2"],
            owner_intent="buy",
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

        filtered_buy_requests = []
        today = date.today()
        tomorrow = today + timedelta(days=1)

        for exchange in buy_requests:
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

            filtered_buy_requests.append(exchange)

        # Применяем сортировку
        # Используем составной ключ сортировки для корректной работы с несколькими критериями
        def sort_key(exchange):
            # Определяем направление сортировки для даты
            date_multiplier = 1 if date_sort_value == "nearest" else -1
            # Определяем направление сортировки для оплаты
            price_multiplier = 1 if price_sort_value == "cheap" else -1

            # Возвращаем кортеж (дата, оплата) с учетом направления сортировки
            # Используем timestamp для корректной обработки отрицательных значений
            return (
                date_multiplier * exchange.start_time.timestamp(),
                price_multiplier * exchange.price,
            )

        filtered_buy_requests.sort(key=sort_key)

        # Форматируем данные для отображения
        available_buy_requests = []
        for exchange in filtered_buy_requests:
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
                "owner_id": exchange.owner_id,  # Создатель запроса покупки
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

        # Показываем сортировку по оплате всегда (вторичный критерий)
        if price_sort_value == "cheap":
            sorting_text_parts.append("По оплате: 💰 Сначала дешевые")
        else:
            sorting_text_parts.append("По оплате: 💸 Сначала дорогие")

        sorting_text = "\n".join(sorting_text_parts)

        # Определяем, отличаются ли настройки от значений по умолчанию
        is_default_settings = (
            day_filter_value == "all"
            and shift_filter_value == "all"
            and date_sort_value == "nearest"
            and price_sort_value == "cheap"
        )

        default_filters = day_filter_value == "all" and shift_filter_value == "all"
        default_sorting = date_sort_value == "nearest" and price_sort_value == "cheap"

        return {
            "available_buy_requests": available_buy_requests,
            "buy_requests_length": len(available_buy_requests),
            "has_buy_requests": len(available_buy_requests) > 0,
            "active_filters": filters_text,
            "active_sorting": sorting_text,
            "has_active_filters": not default_filters,
            "has_active_sorting": not default_sorting,
            "show_reset_button": not is_default_settings,
        }

    except Exception:
        return {
            "available_buy_requests": [],
            "has_buy_requests": False,
            "active_filters": "Период: 📅 Все дни\nСмена: ⭐ Все",
            "active_sorting": "По дате: 📈 Сначала ближайшие\nПо оплате: 💰 Сначала дешевые",
            "has_active_sorting": True,
            "has_active_filters": True,
            "show_reset_button": False,
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
        seller = await stp_repo.employee.get_users(user_id=exchange.owner_id)

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

        exchange_info = await get_exchange_text(stp_repo, exchange, user.user_id)
        deeplink = f"exchange_{exchange.id}"

        return {
            "exchange_info": exchange_info,
            "deeplink": deeplink,
        }

    except Exception as e:
        logger.error(f"[Биржа] Ошибка при просмотре сделки: {e}")
        return {"error": "Ошибка загрузки данных"}


async def my_exchanges(
    stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для отображения всех сделок пользователя.

    Args:
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь сделок пользователя
    """
    user_id = dialog_manager.event.from_user.id

    try:
        exchanges_filter: ManagedRadio = dialog_manager.find("exchanges_filter")
        current_filter = exchanges_filter.get_checked()

        intent = None
        match current_filter:
            case "sell":
                intent = "sell"
            case "buy":
                intent = "buy"
        exchanges = await stp_repo.exchange.get_user_exchanges(
            user_id=user_id,
            intent=intent,
        )

        # Форматируем данные для отображения
        my_exchanges_list = []
        for exchange in exchanges:
            # Форматируем дату из start_time с защитой от None
            if exchange.start_time:
                date_str = exchange.start_time.strftime("%d.%m")
            else:
                date_str = "Не указано"

            # Генерируем текст кнопки с помощью универсальной функции
            button_text = await _get_exchange_button_text(exchange, user_id, date_str)

            my_exchanges_list.append({
                "id": exchange.id,
                "button_text": button_text,
                "type": exchange.owner_intent,
                "status": exchange.status,
                "is_seller": exchange.owner_id == user_id,
                "date": date_str,
                "time": f"{exchange.start_time.strftime('%H:%M') if exchange.start_time else 'Не указано'}-{exchange.end_time.strftime('%H:%M') if exchange.end_time else 'Не указано'}".rstrip(
                    "-"
                ),
                "price": exchange.price,
            })

        exchanges_query = "my_exchanges"
        exchanges_types = [
            ("all", "Все"),
            ("sell", "📉 Продажа"),
            ("buy", "📈 Покупка"),
        ]

        return {
            "my_exchanges": my_exchanges_list,
            "length": len(my_exchanges_list),
            "has_exchanges": len(my_exchanges_list) > 0,
            "exchanges_deeplink": exchanges_query,
            "exchanges_types": exchanges_types,
        }

    except Exception:
        return {
            "my_exchanges": [],
            "has_exchanges": False,
        }


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
    is_seller = exchange.owner_id == dialog_manager.event.from_user.id

    # Установка чекбоксов
    in_schedule: ManagedCheckbox = dialog_manager.find(
        "exchange_in_schedule"
    )  # В графике
    await in_schedule.set_checked(
        exchange.in_owner_schedule if is_seller else exchange.in_counterpart_schedule
    )

    if exchange.owner_intent == "sell":
        # Для продажи: seller_id отдает смену и платит, buyer_id берет смену и получает оплату
        current_user_should_get_paid = (
            exchange.counterpart_id == dialog_manager.event.from_user.id
        )
    else:  # exchange.owner_intent == "buy"
        # Для запроса покупки: seller_id хочет взять смену и получить оплату, buyer_id отдает смену и платит
        current_user_should_get_paid = (
            exchange.owner_id == dialog_manager.event.from_user.id
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

    exchange_text = await get_exchange_text(
        stp_repo, exchange, user.user_id, show_detailed_roles=True
    )
    exchange_status = await _get_exchange_status(exchange)
    exchange_type = await _get_exchange_type(exchange)

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
    ] and tz_perm.localize(exchange.start_time) > datetime.now(tz=tz_perm)

    can_cancel = (
        exchange.status == "sold"
        and exchange.start_time
        and tz_perm.localize(exchange.start_time) > datetime.now(tz=tz_perm)
    )

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
        "current_user_should_get_paid": current_user_should_get_paid,
        "can_cancel": can_cancel,
    }


async def my_detail_edit_getter(
    stp_repo: MainRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
):
    """Геттер для настроек сделки."""
    exchange_id = (
        dialog_manager.dialog_data.get("exchange_id", None)
        or dialog_manager.start_data["exchange_id"]
    )

    exchange = await stp_repo.exchange.get_exchange_by_id(exchange_id)
    return {"status": exchange.status}


async def buy_time_selection_getter(
    stp_repo: MainRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> Dict[str, Any]:
    """Геттер для экрана выбора времени покупки."""
    original_exchange = dialog_manager.dialog_data.get("original_exchange")

    if not original_exchange:
        return {"error": "Обмен не найден"}

    # Получаем информацию об обмене
    start_time = original_exchange["start_time"].strftime("%H:%M")
    end_time = original_exchange["end_time"].strftime("%H:%M")
    date_str = original_exchange["start_time"].strftime("%d.%m.%Y")

    # Рассчитываем общее количество часов
    duration = original_exchange["end_time"] - original_exchange["start_time"]
    total_hours = duration.total_seconds() / 3600

    # Рассчитываем общую стоимость (цена за час * количество часов)
    price_per_hour = original_exchange["price"]
    total_price = int(price_per_hour * total_hours)

    return {
        "start_time": start_time,
        "end_time": end_time,
        "date_str": date_str,
        "total_hours": f"{total_hours:g}",
        "price_per_hour": price_per_hour,
        "total_price": total_price,
        "time_range": f"{start_time}-{end_time}",
    }


async def buy_confirmation_getter(
    stp_repo: MainRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> Dict[str, Any]:
    """Геттер для экрана подтверждения покупки."""
    original_exchange = dialog_manager.dialog_data.get("original_exchange")
    buy_full = dialog_manager.dialog_data.get("buy_full", False)

    if not original_exchange:
        return {"error": "Обмен не найден"}

    # Получаем информацию о продавце
    seller = await stp_repo.employee.get_users(user_id=original_exchange["owner_id"])
    seller_name = format_fullname(seller, True, True)

    date_str = original_exchange["start_time"].strftime("%d.%m.%Y")
    price_per_hour = original_exchange["price"]

    if buy_full:
        # Полная покупка
        start_time = original_exchange["start_time"].strftime("%H:%M")
        end_time = original_exchange["end_time"].strftime("%H:%M")
        duration = original_exchange["end_time"] - original_exchange["start_time"]
        hours = duration.total_seconds() / 3600
        total_price = int(price_per_hour * hours)
        time_range = f"{start_time}-{end_time}"
        purchase_type = "Полная покупка смены"
    else:
        # Частичная покупка
        start_str = dialog_manager.dialog_data.get("selected_start_time")
        end_str = dialog_manager.dialog_data.get("selected_end_time")

        from datetime import datetime

        exchange_date = original_exchange["start_time"].date()
        selected_start = datetime.combine(
            exchange_date, datetime.strptime(start_str, "%H:%M").time()
        )
        selected_end = datetime.combine(
            exchange_date, datetime.strptime(end_str, "%H:%M").time()
        )

        # Рассчитываем цену исходя из цены за час
        selected_duration = selected_end - selected_start
        hours = selected_duration.total_seconds() / 3600
        total_price = int(price_per_hour * hours)

        time_range = f"{start_str}-{end_str}"
        purchase_type = "Частичная покупка смены"

    return {
        "purchase_type": purchase_type,
        "date_str": date_str,
        "time_range": time_range,
        "hours": f"{hours:g}",
        "price_per_hour": price_per_hour,
        "total_price": total_price,
        "seller_name": seller_name,
        "buy_full": buy_full,
    }


# New getters for seller responding to buy requests


async def sell_time_selection_getter(
    stp_repo: MainRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> Dict[str, Any]:
    """Геттер для экрана выбора времени продавцом в ответ на buy request."""
    buy_request = dialog_manager.dialog_data.get("buy_request")

    if not buy_request:
        return {"error": "Buy request не найден"}

    # Получаем информацию о покупателе
    buyer = await stp_repo.employee.get_users(user_id=buy_request["owner_id"])
    buyer_name = format_fullname(buyer, True, True)

    # Форматируем время и дату
    start_time = buy_request["start_time"].strftime("%H:%M")
    end_time = buy_request["end_time"].strftime("%H:%M")
    date_str = buy_request["start_time"].strftime("%d.%m.%Y")

    # Рассчитываем общее количество часов
    duration = buy_request["end_time"] - buy_request["start_time"]
    requested_hours = duration.total_seconds() / 3600

    return {
        "buyer_name": buyer_name,
        "date_str": date_str,
        "requested_time_range": f"{start_time}-{end_time}",
        "requested_hours": f"{requested_hours:g}",
        "price_per_hour": buy_request["price"],
    }


async def sell_confirmation_getter(
    stp_repo: MainRequestsRepo,
    dialog_manager: DialogManager,
    **_kwargs,
) -> Dict[str, Any]:
    """Геттер для экрана подтверждения предложения продажи."""
    buy_request = dialog_manager.dialog_data.get("buy_request")
    offer_full = dialog_manager.dialog_data.get("offer_full", False)

    if not buy_request:
        return {"error": "Buy request не найден"}

    # Получаем информацию о покупателе
    buyer = await stp_repo.employee.get_users(user_id=buy_request["owner_id"])
    buyer_name = format_fullname(buyer, True, True)

    date_str = buy_request["start_time"].strftime("%d.%m.%Y")
    price_per_hour = buy_request["price"]

    # Форматируем запрашиваемое время
    request_start = buy_request["start_time"].strftime("%H:%M")
    request_end = buy_request["end_time"].strftime("%H:%M")
    request_duration = buy_request["end_time"] - buy_request["start_time"]
    requested_hours = request_duration.total_seconds() / 3600

    if offer_full:
        # Предлагаем всё запрашиваемое время
        offered_time_range = f"{request_start}-{request_end}"
        offered_hours = requested_hours
        total_price = int(price_per_hour * offered_hours)
    else:
        # Частичное предложение времени
        start_str = dialog_manager.dialog_data.get("offered_start_time")
        end_str = dialog_manager.dialog_data.get("offered_end_time")

        from datetime import datetime

        request_date = buy_request["start_time"].date()
        offered_start = datetime.combine(
            request_date, datetime.strptime(start_str, "%H:%M").time()
        )
        offered_end = datetime.combine(
            request_date, datetime.strptime(end_str, "%H:%M").time()
        )

        # Рассчитываем цену исходя из цены за час
        offered_duration = offered_end - offered_start
        offered_hours = offered_duration.total_seconds() / 3600
        total_price = int(price_per_hour * offered_hours)

        offered_time_range = f"{start_str}-{end_str}"

    return {
        "buyer_name": buyer_name,
        "date_str": date_str,
        "requested_time_range": f"{request_start}-{request_end}",
        "requested_hours": f"{requested_hours:g}",
        "time_range": offered_time_range,
        "offered_hours": f"{offered_hours:g}",
        "price_per_hour": price_per_hour,
        "total_price": total_price,
        "offer_full": offer_full,
    }

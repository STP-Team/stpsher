"""Геттеры для подписок на биржу."""

import logging
from typing import Any, Dict

from aiogram import Bot
from aiogram.utils.deep_linking import create_start_link
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import ManagedCheckbox, ManagedRadio, ManagedToggle
from stp_database import Employee, MainRequestsRepo

from tgbot.handlers.inline.helpers import EXCHANGE_TYPE_NAMES
from tgbot.misc.helpers import DAY_NAMES, short_name

logger = logging.getLogger(__name__)


async def subscriptions_getter(
    stp_repo: MainRequestsRepo, user: Employee, **_kwargs
) -> Dict[str, Any]:
    """Геттер для списка подписок пользователя.

    Args:
        stp_repo: Репозиторий операций с базой STP
        user: Экземпляр пользователя с моделью Employee

    Returns:
        Словарь с подписками пользователя
    """
    try:
        # Получаем подписки пользователя
        subscriptions = await stp_repo.exchange.get_user_subscriptions(
            user.user_id, active_only=False
        )

        active_subscriptions = [s for s in subscriptions if s.is_active]

        # Форматируем для отображения
        subscriptions_list = []
        for sub in subscriptions:
            status = "🟢 Активна" if sub.is_active else "🔴 Отключена"
            name = sub.name or "Без названия"

            subscriptions_list.append({
                "id": sub.id,
                "name": name,
                "status": status,
            })

        return {
            "subscriptions_list": subscriptions_list,
            "has_subscriptions": len(subscriptions) > 0,
            "active_subscriptions_count": len(active_subscriptions),
            "total_subscriptions_count": len(subscriptions),
        }

    except Exception as e:
        logger.error(f"Ошибка получения подписок для пользователя {user.user_id}: {e}")
        return {
            "subscriptions_list": [],
            "has_subscriptions": False,
            "active_subscriptions_count": 0,
            "total_subscriptions_count": 0,
        }


async def subscription_detail_getter(
    stp_repo: MainRequestsRepo,
    user: Employee,
    bot: Bot,
    dialog_manager: DialogManager,
    **_kwargs,
) -> Dict[str, Any]:
    """Геттер для деталей конкретной подписки.

    Args:
        bot: Экземпляр бота
        stp_repo: Репозиторий операций с базой STP
        user: Экземпляр пользователя с моделью Employee
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с деталями подписки
    """
    try:
        subscription_id = (
            dialog_manager.dialog_data.get("subscription_id", None)
            or dialog_manager.start_data["subscription_id"]
        )

        # Получаем подписку
        subscription = await stp_repo.exchange.get_subscription_by_id(
            subscription_id, user.user_id
        )

        # Установка чекбоксов
        sub_status_checkbox: ManagedCheckbox = dialog_manager.find("sub_status")
        await sub_status_checkbox.set_checked(bool(subscription.is_active))

        # Форматируем критерии
        criteria_parts = []
        if subscription.min_price:
            criteria_parts.append(f"• Минимальная цена: {subscription.min_price} р.")
        if subscription.max_price:
            criteria_parts.append(f"• Максимальная цена: {subscription.max_price} р.")
        if subscription.start_time and subscription.end_time:
            criteria_parts.append(
                f"• Время: с {subscription.start_time.strftime('%H:%M')} до {subscription.end_time.strftime('%H:%M')}"
            )
        if subscription.days_of_week:
            days_text = ", ".join([
                DAY_NAMES.get(d, str(d)) for d in subscription.days_of_week
            ])
            criteria_parts.append(f"• Дни: {days_text}")

        # Проверяем наличие выбранного сотрудника
        if subscription.target_seller_id:
            try:
                target_seller = await stp_repo.employee.get_users(
                    user_id=subscription.target_seller_id
                )
                if target_seller:
                    seller_short = short_name(target_seller.fullname)
                    criteria_parts.append(f"• Сотрудник: {seller_short}")
            except Exception as e:
                logger.error(
                    f"Ошибка получения информации о сотруднике {subscription.target_seller_id}: {e}"
                )

        criteria_text = "\n".join(criteria_parts) if criteria_parts else "• Все обмены"

        # Форматируем тип обмена
        exchange_type = EXCHANGE_TYPE_NAMES.get(
            subscription.exchange_type, subscription.exchange_type
        )

        deeplink = f"subscription_{subscription_id}"
        deeplink_url = await create_start_link(bot=bot, payload=deeplink, encode=True)

        return {
            "subscription_name": subscription.name,
            "exchange_type": exchange_type,
            "criteria_text": criteria_text,
            "status": subscription.is_active,
            "deeplink": deeplink,
            "deeplink_url": deeplink_url,
        }

    except Exception as e:
        logger.error(f"Ошибка получения деталей подписки {subscription_id}: {e}")
        return {
            "subscription_name": "Ошибка загрузки",
            "exchange_type": "Неизвестно",
            "criteria_text": "Ошибка загрузки критериев",
        }


async def subscription_create_type_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для выбора типа подписки.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с типами обменов
    """
    exchange_types = [
        ("buy", "📈 Покупка часов (я покупаю)"),
        ("sell", "📉 Продажа часов (я продаю)"),
        ("both", "🔄 Оба типа"),
    ]

    sub_type = dialog_manager.dialog_data.get("type")

    return {
        "exchange_types": exchange_types,
        "exchange_type_selected": sub_type is not None,
    }


async def subscription_create_criteria_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для выбора критериев подписки.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с критериями
    """
    # Получаем выбранный тип обменов (автоматический или из виджета)
    sub_type = dialog_manager.dialog_data.get("type")

    type_names = {
        "buy": "📈 Покупка часов",
        "sell": "📉 Продажа часов",
        "both": "🔄 Оба типа",
    }

    criteria_options = [
        ("price", "💰 По цене"),
        ("time", "⏰ По времени"),
        ("days", "📅 По дням недели"),
        ("seller", "👤 По сотруднику"),
    ]

    # Проверяем выбранные критерии
    criteria_widget: ManagedToggle = dialog_manager.find("criteria_toggles")
    selected_criteria = criteria_widget.get_checked() if criteria_widget else []

    # Формируем отображение выбранных критериев для блокквота
    criteria_names = {
        "price": "💰 По цене",
        "time": "⏰ По времени",
        "days": "📅 По дням недели",
        "seller": "👤 По сотруднику",
    }

    if selected_criteria:
        current_criteria_display = "🎯 <b>Критерии:</b>\n" + "\n".join([
            criteria_names.get(c, c) for c in selected_criteria
        ])
    else:
        current_criteria_display = "🎯 <b>Критерии:</b> не выбраны"

    return {
        "selected_exchange_type": type_names.get(sub_type, "Не выбрано"),
        "criteria_options": criteria_options,
        "criteria_selected": len(selected_criteria) > 0,
        "current_criteria_display": current_criteria_display,
    }


async def subscription_create_price_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для настройки цены.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с настройками цены
    """
    sub_type = dialog_manager.dialog_data.get("type")

    type_names = {
        "buy": "📈 Покупка часов",
        "sell": "📉 Продажа часов",
        "both": "🔄 Оба типа",
    }

    # Получаем выбранные критерии
    criteria_widget: ManagedToggle = dialog_manager.find("criteria_toggles")
    selected_criteria = criteria_widget.get_checked() if criteria_widget else []

    criteria_names = {
        "price": "💰 По цене",
        "time": "⏰ По времени",
        "days": "📅 По дням недели",
        "seller": "👤 По сотруднику",
    }

    selected_criteria_text = ", ".join([
        criteria_names.get(c, c) for c in selected_criteria
    ])

    # Состояние ввода цены
    price_data = dialog_manager.dialog_data.get("price_data", {})
    input_step = price_data.get("step", "min")  # "min" или "max"

    # Формируем отображение настроек цены
    price_settings = []
    if price_data.get("min_price"):
        price_settings.append(f"от {price_data['min_price']} р.")
    if price_data.get("max_price"):
        price_settings.append(f"до {price_data['max_price']} р.")

    if price_settings:
        price_settings_display = "\n💰 <b>Цена:</b> " + " ".join(price_settings)
    else:
        price_settings_display = "\n💰 <b>Цена:</b> настраиваем сейчас"

    return {
        "exchange_type_display": type_names.get(sub_type, "Не выбрано"),
        "criteria_display": selected_criteria_text or "все обмены",
        "price_settings_display": price_settings_display,
        "selected_criteria": selected_criteria_text,
        "min_price": price_data.get("min_price"),
        "max_price": price_data.get("max_price"),
        "input_step_min": input_step == "min",
        "input_step_max": input_step == "max",
        "input_step_active": True,
        "price_completed": price_data.get("completed", False),
    }


async def subscription_create_time_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для настройки времени.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с временными диапазонами
    """
    sub_type = dialog_manager.dialog_data.get("type")

    type_names = {
        "buy": "📈 Покупка часов",
        "sell": "📉 Продажа часов",
        "both": "🔄 Оба типа",
    }

    # Получаем выбранные критерии для отображения
    criteria_widget: ManagedToggle = dialog_manager.find("criteria_toggles")
    selected_criteria = criteria_widget.get_checked() if criteria_widget else []

    criteria_names = {
        "price": "💰 По цене",
        "time": "⏰ По времени",
        "days": "📅 По дням недели",
        "seller": "👤 По сотруднику",
    }

    criteria_display = (
        ", ".join([criteria_names.get(c, c) for c in selected_criteria]) or "все обмены"
    )

    # Формируем отображение уже настроенных параметров
    settings_parts = []

    # Цена
    price_data = dialog_manager.dialog_data.get("price_data", {})
    if price_data.get("min_price") or price_data.get("max_price"):
        price_parts = []
        if price_data.get("min_price"):
            price_parts.append(f"от {price_data['min_price']} р.")
        if price_data.get("max_price"):
            price_parts.append(f"до {price_data['max_price']} р.")
        settings_parts.append("💰 Цена: " + " ".join(price_parts))

    # Время (текущий этап)
    time_widget: ManagedRadio = dialog_manager.find("time_range")
    selected_time = time_widget.get_checked() if time_widget else None
    if selected_time:
        time_names = {
            "morning": "утро (06:00-12:00)",
            "afternoon": "день (12:00-18:00)",
            "evening": "вечер (18:00-24:00)",
            "night": "ночь (00:00-06:00)",
            "work_hours": "рабочие часы (08:00-20:00)",
        }
        settings_parts.append(
            f"⏰ <b>Время:</b> {time_names.get(selected_time, selected_time)}"
        )
    else:
        settings_parts.append("⏰ <b>Время:</b> настраиваем сейчас")

    current_settings_display = (
        "\n" + "\n".join(settings_parts) if settings_parts else ""
    )

    time_ranges = [
        ("morning", "🌅 Утро (06:00-12:00)"),
        ("afternoon", "☀️ День (12:00-18:00)"),
        ("evening", "🌆 Вечер (18:00-24:00)"),
        ("night", "🌙 Ночь (00:00-06:00)"),
        ("work_hours", "🕘 Рабочие часы (08:00-20:00)"),
    ]

    return {
        "exchange_type_display": type_names.get(sub_type, "Не выбрано"),
        "criteria_display": criteria_display,
        "current_settings_display": current_settings_display,
        "selected_criteria": ", ".join([
            criteria_names.get(c, c) for c in selected_criteria
        ]),
        "time_ranges": time_ranges,
        "time_selected": selected_time is not None,
    }


async def subscription_create_date_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для настройки дней недели.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с днями недели
    """
    sub_type = dialog_manager.dialog_data.get("type")

    type_names = {
        "buy": "📈 Покупка часов",
        "sell": "📉 Продажа часов",
        "both": "🔄 Оба типа",
    }

    # Получаем выбранные критерии
    criteria_widget: ManagedToggle = dialog_manager.find("criteria_toggles")
    selected_criteria = criteria_widget.get_checked() if criteria_widget else []

    criteria_names = {
        "price": "💰 По цене",
        "time": "⏰ По времени",
        "days": "📅 По дням недели",
        "seller": "👤 По сотруднику",
    }

    criteria_display = (
        ", ".join([criteria_names.get(c, c) for c in selected_criteria]) or "все обмены"
    )

    # Формируем отображение уже настроенных параметров
    settings_parts = []

    # Цена
    price_data = dialog_manager.dialog_data.get("price_data", {})
    if price_data.get("min_price") or price_data.get("max_price"):
        price_parts = []
        if price_data.get("min_price"):
            price_parts.append(f"от {price_data['min_price']} р.")
        if price_data.get("max_price"):
            price_parts.append(f"до {price_data['max_price']} р.")
        settings_parts.append("💰 Цена: " + " ".join(price_parts))

    # Время
    time_widget: ManagedRadio = dialog_manager.find("time_range")
    selected_time = time_widget.get_checked() if time_widget else None
    if selected_time:
        time_names = {
            "morning": "утро (06:00-12:00)",
            "afternoon": "день (12:00-18:00)",
            "evening": "вечер (18:00-24:00)",
            "night": "ночь (00:00-06:00)",
            "work_hours": "рабочие часы (08:00-20:00)",
            "all_day": "круглосуточно",
        }
        settings_parts.append(
            f"⏰ Время: {time_names.get(selected_time, selected_time)}"
        )

    # Дни недели (текущий этап)
    days_widget: ManagedToggle = dialog_manager.find("days_of_week")
    selected_days = days_widget.get_checked() if days_widget else []
    if selected_days:
        # Convert string keys to int for DAY_NAMES lookup
        days_text = ", ".join([DAY_NAMES.get(int(d), d) for d in selected_days])
        settings_parts.append(f"📅 <b>Дни:</b> {days_text}")
    else:
        settings_parts.append("📅 <b>Дни:</b> настраиваем сейчас")

    current_settings_display = (
        "\n" + "\n".join(settings_parts) if settings_parts else ""
    )

    weekdays = [
        ("1", "Понедельник"),
        ("2", "Вторник"),
        ("3", "Среда"),
        ("4", "Четверг"),
        ("5", "Пятница"),
        ("6", "Суббота"),
        ("7", "Воскресенье"),
    ]

    return {
        "exchange_type_display": type_names.get(sub_type, "Не выбрано"),
        "criteria_display": criteria_display,
        "current_settings_display": current_settings_display,
        "selected_criteria": _get_criteria_summary(dialog_manager),
        "weekdays": weekdays,
        "days_selected": len(selected_days) > 0,
    }


async def subscription_create_confirmation_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для подтверждения создания подписки.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с финальной информацией о подписке
    """
    # Автоматически генерируем название подписки если его нет
    auto_name = _generate_subscription_name(dialog_manager)
    dialog_manager.dialog_data["subscription_name"] = auto_name

    subscription_name = dialog_manager.dialog_data.get(
        "subscription_name", "Моя подписка"
    )

    sub_type = dialog_manager.dialog_data.get("type")
    type_names = {
        "buy": "📈 Покупка часов",
        "sell": "📉 Продажа часов",
        "both": "🔄 Оба типа",
    }
    exchange_type = type_names.get(sub_type, "Не выбрано")

    # Детальная сводка критериев
    criteria_summary = _get_detailed_criteria_summary(dialog_manager)

    # Сводка уведомлений
    notification_summary = _get_notification_summary(dialog_manager)

    return {
        "subscription_name": subscription_name,
        "exchange_type": exchange_type,
        "criteria_summary": criteria_summary,
        "notification_summary": notification_summary,
    }


def _generate_subscription_name(dialog_manager: DialogManager) -> str:
    """Генерирует автоматическое название для подписки.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Сгенерированное название
    """
    parts = []

    sub_type = dialog_manager.dialog_data.get("type")
    type_names = {"buy": "Покупка", "sell": "Продажа", "both": "Все обмены"}
    parts.append(type_names.get(sub_type, "Обмены"))

    # Сотрудник (приоритетно)
    selected_seller_name = dialog_manager.dialog_data.get("selected_seller_name")
    if selected_seller_name:
        seller_short = short_name(selected_seller_name)
        parts.append(f"от {seller_short}")

    # Цена
    price_data = dialog_manager.dialog_data.get("price_data", {})
    if price_data.get("max_price"):
        parts.append(f"до {price_data['max_price']}р")
    elif price_data.get("min_price"):
        parts.append(f"от {price_data['min_price']}р")

    # Время
    time_widget: ManagedRadio = dialog_manager.find("time_range")
    selected_time = time_widget.get_checked() if time_widget else None
    if selected_time:
        time_names = {
            "morning": "утром",
            "afternoon": "днем",
            "evening": "вечером",
            "work_hours": "в раб.часы",
        }
        if selected_time in time_names:
            parts.append(time_names[selected_time])

    # Дни недели
    days_widget: ManagedToggle = dialog_manager.find("days_of_week")
    selected_days = days_widget.get_checked() if days_widget else []
    if selected_days and len(selected_days) < 7:
        if set(selected_days) == {"6", "7"}:
            parts.append("в выходные")
        elif set(selected_days) == {"1", "2", "3", "4", "5"}:
            parts.append("в будни")

    return " ".join(parts) if parts else "Моя подписка"


def _get_criteria_summary(dialog_manager: DialogManager) -> str:
    """Получить краткую сводку выбранных критериев."""
    criteria_widget: ManagedToggle = dialog_manager.find("criteria_toggles")
    selected_criteria = criteria_widget.get_checked() if criteria_widget else []

    criteria_names = {
        "price": "💰 Цена",
        "time": "⏰ Время",
        "days": "📅 Дни недели",
        "seller": "👤 Продавец",
    }

    criteria_parts = [criteria_names.get(c, c) for c in selected_criteria]

    # Добавляем уже настроенные значения
    price_data = dialog_manager.dialog_data.get("price_data", {})
    if price_data.get("min_price"):
        criteria_parts.append(f"от {price_data['min_price']} р.")
    if price_data.get("max_price"):
        criteria_parts.append(f"до {price_data['max_price']} р.")

    # Добавляем выбранного сотрудника
    selected_seller_name = dialog_manager.dialog_data.get("selected_seller_name")
    if selected_seller_name:
        seller_short = short_name(selected_seller_name)
        criteria_parts.append(f"от {seller_short}")

    return ", ".join(criteria_parts) if criteria_parts else "Все обмены"


def _get_subscription_summary(dialog_manager: DialogManager) -> str:
    """Получить краткое описание подписки для названия."""
    sub_type = dialog_manager.dialog_data.get("type")
    type_short = {"buy": "покупка", "sell": "продажа", "both": "все обмены"}

    criteria_summary = _get_criteria_summary(dialog_manager)

    return f"{type_short.get(sub_type, 'обмены')}: {criteria_summary}"


def _get_detailed_criteria_summary(dialog_manager: DialogManager) -> str:
    """Получить детальную сводку критериев."""
    criteria_parts = []

    # Цена
    price_data = dialog_manager.dialog_data.get("price_data", {})
    if price_data.get("min_price") or price_data.get("max_price"):
        price_parts = []
        if price_data.get("min_price"):
            price_parts.append(f"от {price_data['min_price']} р.")
        if price_data.get("max_price"):
            price_parts.append(f"до {price_data['max_price']} р.")
        criteria_parts.append(f"• Цена: {' '.join(price_parts)}")

    # Время
    time_widget: ManagedRadio = dialog_manager.find("time_range")
    selected_time = time_widget.get_checked() if time_widget else None
    if selected_time:
        time_names = {
            "morning": "утро (06:00-12:00)",
            "afternoon": "день (12:00-18:00)",
            "evening": "вечер (18:00-24:00)",
            "night": "ночь (00:00-06:00)",
            "work_hours": "рабочие часы (08:00-20:00)",
            "all_day": "круглосуточно",
        }
        criteria_parts.append(
            f"• Время: {time_names.get(selected_time, selected_time)}"
        )

    # Дни недели
    days_widget: ManagedToggle = dialog_manager.find("days_of_week")
    selected_days = days_widget.get_checked() if days_widget else []
    if selected_days:
        # Convert string keys to int for DAY_NAMES lookup
        days_text = ", ".join([DAY_NAMES.get(int(d), d) for d in selected_days])
        criteria_parts.append(f"• Дни: {days_text}")

    # Сотрудник
    selected_seller_name = dialog_manager.dialog_data.get("selected_seller_name")
    if selected_seller_name:
        seller_short = short_name(selected_seller_name)
        criteria_parts.append(f"• Сотрудник: {seller_short}")

    return "\n".join(criteria_parts) if criteria_parts else "• Все обмены"


def _get_notification_summary(dialog_manager: DialogManager) -> str:
    """Получить сводку настроек уведомлений."""
    # Всегда включены мгновенные уведомления о новых/отредактированных обменах
    return "• Мгновенные уведомления о новых и отредактированных обменах"


async def subscription_create_seller_search_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для поиска сотрудника для подписки.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с данными для поиска сотрудника
    """
    sub_type = dialog_manager.dialog_data.get("type")

    type_names = {
        "buy": "📈 Покупка часов",
        "sell": "📉 Продажа часов",
        "both": "🔄 Оба типа",
    }

    # Получаем выбранные критерии для отображения
    criteria_widget: ManagedToggle = dialog_manager.find("criteria_toggles")
    selected_criteria = criteria_widget.get_checked() if criteria_widget else []

    criteria_names = {
        "price": "💰 По цене",
        "time": "⏰ По времени",
        "days": "📅 По дням недели",
        "seller": "👤 По сотруднику",
    }

    criteria_display = (
        ", ".join([criteria_names.get(c, c) for c in selected_criteria]) or "все обмены"
    )

    return {
        "exchange_type_display": type_names.get(sub_type, "Не выбрано"),
        "criteria_display": criteria_display,
    }


async def subscription_create_seller_results_getter(
    dialog_manager: DialogManager, **_kwargs
) -> Dict[str, Any]:
    """Геттер для результатов поиска сотрудника.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с результатами поиска
    """
    search_results = dialog_manager.dialog_data.get("seller_search_results", [])
    search_query = dialog_manager.dialog_data.get("seller_search_query", "")
    total_found = dialog_manager.dialog_data.get("seller_search_total", 0)

    return {
        "search_results": search_results,
        "search_query": search_query,
        "total_found": total_found,
        "has_results": len(search_results) > 0,
    }

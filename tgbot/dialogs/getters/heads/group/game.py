"""Геттеры для игровых функций группы."""

from datetime import datetime
from typing import Any

from aiogram_dialog import DialogManager
from stp_database import Employee, MainRequestsRepo

from tgbot.misc.helpers import format_fullname, get_status_emoji, strftime_date
from tgbot.services.leveling import LevelingSystem

# Словарь для русских названий месяцев
RUSSIAN_MONTHS = {
    1: "январь",
    2: "февраль",
    3: "март",
    4: "апрель",
    5: "май",
    6: "июнь",
    7: "июль",
    8: "август",
    9: "сентябрь",
    10: "октябрь",
    11: "ноябрь",
    12: "декабрь",
}


async def game_statistics_getter(
    user: Employee, stp_repo: MainRequestsRepo, **_kwargs
) -> dict[str, Any]:
    """Геттер для получения статистики группы.

    Args:
        user: Экземпляр пользователя с моделью Employee (руководитель)
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь со статистикой группы
    """
    # Получаем всех пользователей группы
    group_members = await stp_repo.employee.get_users(head=user.fullname)

    if not group_members:
        return {
            "statistics_text": "❌ В твоей группе нет сотрудников",
            "total_balance": 0,
            "avg_level": 0,
        }

    # Получаем текущий месяц и год
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    month_name = f"{RUSSIAN_MONTHS[current_month]} {current_year}"

    # Оптимизация: собираем все данные за один проход
    total_balance = 0
    total_level = 0
    month_balances = {}
    members_with_balance = []

    for member in group_members:
        # Получаем баланс
        balance = await stp_repo.transaction.get_user_balance(member.user_id)
        total_balance += balance
        members_with_balance.append((member, balance))

        # Получаем сумму баллов за достижения для расчета уровня
        achievements_sum = await stp_repo.transaction.get_user_achievements_sum(
            member.user_id
        )
        level = LevelingSystem.calculate_level(achievements_sum)
        total_level += level

        # Получаем транзакции за текущий месяц для этого пользователя
        transactions = await stp_repo.transaction.get_user_transactions(
            user_id=member.user_id
        )
        member_month_sum = sum(
            t.amount
            for t in transactions
            if t.created_at.month == current_month and t.created_at.year == current_year
        )
        month_balances[member.user_id] = (member, member_month_sum)

    avg_level = total_level / len(group_members)

    # Сортируем для топ-3
    month_top = sorted(month_balances.values(), key=lambda x: x[1], reverse=True)[:3]
    all_time_top = sorted(members_with_balance, key=lambda x: x[1], reverse=True)[:3]

    # Форматируем топ-3 за месяц
    month_top_text = []
    medals = ["🥇", "🥈", "🥉"]

    for idx, (member, balance) in enumerate(month_top):
        name = format_fullname(
            member.fullname, True, True, member.username, member.user_id
        )
        month_top_text.append(f"{medals[idx]} {name} - {int(balance)} баллов")

    # Форматируем топ-3 за все время
    all_time_top_text = []
    for idx, (member, balance) in enumerate(all_time_top):
        name = format_fullname(
            member.fullname, True, True, member.username, member.user_id
        )
        all_time_top_text.append(f"{medals[idx]} {name} - {balance} баллов")

    statistics_text = f"""📊 <b>Статистика группы</b>

💎 Общие баллы группы: {total_balance} баллов
⚡️ Средний уровень группы: {int(avg_level)}

🏆 ТОП-3 за {month_name}:
{chr(10).join(month_top_text) if month_top_text else "Нет данных"}

🌟 ТОП-3 за все время:
{chr(10).join(all_time_top_text) if all_time_top_text else "Нет данных"}"""

    return {
        "statistics_text": statistics_text,
        "total_balance": total_balance,
        "avg_level": int(avg_level),
    }


async def game_achievements_getter(
    user: Employee, stp_repo: MainRequestsRepo, **_kwargs
) -> dict[str, Any]:
    """Геттер для получения достижений группы.

    Args:
        user: Экземпляр пользователя с моделью Employee (руководитель)
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь с достижениями группы
    """
    from html import escape

    # Получаем всех пользователей группы
    group_members = await stp_repo.employee.get_users(head=user.fullname)

    if not group_members:
        return {
            "achievements_text": "❌ В твоей группе нет сотрудников",
            "achievements": [],
            "total_achievements": 0,
        }

    # Получаем все транзакции-достижения группы
    all_achievements = []
    for member in group_members:
        transactions = await stp_repo.transaction.get_user_transactions(
            user_id=member.user_id, only_achievements=True
        )
        for transaction in transactions:
            all_achievements.append((member, transaction))

    # Сортируем по дате получения (новые сначала)
    all_achievements.sort(key=lambda x: x[1].created_at, reverse=True)

    # Оптимизация: получаем все уникальные достижения одним запросом
    # Сначала собираем все уникальные ID достижений
    achievement_ids = set(t.source_id for _, t in all_achievements[:50] if t.source_id)

    # Получаем все достижения одним запросом (если есть метод для этого)
    # Иначе кэшируем в словаре
    achievements_cache = {}
    for achievement_id in achievement_ids:
        achievement = await stp_repo.achievement.get_achievements(
            achievement_id=achievement_id
        )
        if achievement:
            achievements_cache[achievement_id] = achievement

    # Форматируем достижения для отображения
    formatted_achievements = []
    for member, transaction in all_achievements[:50]:  # Ограничиваем 50 последними
        if not transaction.source_id:
            continue

        achievement = achievements_cache.get(transaction.source_id)
        if not achievement:
            continue

        period = "Неизвестно"
        match achievement.period:
            case "d":
                period = "Раз в день"
            case "w":
                period = "Раз в неделю"
            case "m":
                period = "Раз в месяц"
            case "A":
                period = "Вручную"

        date_str = transaction.created_at.strftime(strftime_date)
        member_name = format_fullname(
            member.fullname, True, True, member.username, member.user_id
        )

        formatted_achievements.append((
            transaction.id,
            escape(achievement.name),
            transaction.amount,
            escape(achievement.description),
            achievement.position,
            period,
            date_str,
            member_name,
        ))

    return {
        "achievements": formatted_achievements,
        "total_achievements": len(all_achievements),
    }


async def game_products_getter(
    user: Employee, stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> dict[str, Any]:
    """Геттер для получения покупок группы.

    Args:
        user: Экземпляр пользователя с моделью Employee (руководитель)
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с покупками группы
    """
    # Получаем всех пользователей группы
    group_members = await stp_repo.employee.get_users(head=user.fullname)

    if not group_members:
        return {
            "products": [],
            "total_bought": 0,
            "total_shown": 0,
        }

    # Получаем фильтр статуса
    filter_widget = dialog_manager.find("game_inventory_filter")
    filter_type = filter_widget.get_checked() if filter_widget else "all"

    # Получаем все покупки группы
    all_products = []
    for member in group_members:
        user_products = await stp_repo.purchase.get_user_purchases_with_details(
            user_id=member.user_id
        )
        for product in user_products:
            all_products.append((member, product))

    total_bought = len(all_products)

    # Применяем фильтр и форматируем
    formatted_products = []
    for member, product in all_products:
        user_product = product.user_purchase
        product_info = product.product_info

        # Применяем фильтр
        if filter_type != "all" and user_product.status != filter_type:
            continue

        date_str = user_product.bought_at.strftime("%d.%m.%y")
        status_emoji = get_status_emoji(user_product.status)
        usage_info = f"({product.current_usages}/{product.max_usages})"
        member_name = format_fullname(member.fullname, True, True)
        button_text = f"{status_emoji} {usage_info} {product_info.name} - {member_name} ({date_str})"

        formatted_products.append((
            user_product.id,
            button_text,
            product_info.name,
            product_info.description,
            product_info.cost,
            user_product.status,
            product.current_usages,
            product.max_usages,
            member_name,
        ))

    # Сортируем по дате покупки (новые сначала) - оптимизация
    # Создаем словарь для быстрого поиска даты покупки по ID
    purchase_dates = {
        product.user_purchase.id: product.user_purchase.bought_at
        for _, product in all_products
    }
    formatted_products.sort(
        key=lambda x: purchase_dates.get(x[0], datetime.min),
        reverse=True,
    )

    return {
        "products": formatted_products,
        "total_bought": total_bought,
        "total_shown": len(formatted_products),
    }


async def game_balance_history_getter(
    user: Employee, stp_repo: MainRequestsRepo, **_kwargs
) -> dict[str, Any]:
    """Геттер для получения истории баланса группы.

    Args:
        user: Экземпляр пользователя с моделью Employee (руководитель)
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь с историей баланса группы
    """
    # Получаем всех пользователей группы
    group_members = await stp_repo.employee.get_users(head=user.fullname)

    if not group_members:
        return {
            "history": [],
            "total_transactions": 0,
        }

    # Получаем все транзакции группы
    all_transactions = []
    for member in group_members:
        transactions = await stp_repo.transaction.get_user_transactions(
            user_id=member.user_id
        )
        for transaction in transactions:
            all_transactions.append((member, transaction))

    # Сортируем по дате (новые сначала)
    all_transactions.sort(key=lambda x: x[1].created_at, reverse=True)

    # Форматируем транзакции для отображения (последние 100)
    formatted_history = []
    for member, transaction in all_transactions[:100]:
        date_str = transaction.created_at.strftime(strftime_date)
        member_name = format_fullname(member.fullname, True, True)

        # Определяем тип транзакции
        transaction_type = "Неизвестно"
        if transaction.type == "achievement":
            transaction_type = "Достижение"
        elif transaction.type == "purchase":
            transaction_type = "Покупка"
        elif transaction.type == "casino":
            transaction_type = "Казино"
        elif transaction.type == "manual":
            transaction_type = "Ручное начисление"

        # Форматируем сумму со знаком
        amount_str = (
            f"+{transaction.amount}"
            if transaction.amount > 0
            else str(transaction.amount)
        )

        formatted_history.append((
            transaction.id,
            member_name,
            amount_str,
            transaction_type,
            date_str,
            transaction.comment or "—",
        ))

    return {
        "history": formatted_history,
        "total_transactions": len(all_transactions),
    }


async def game_casino_getter(
    user: Employee, stp_repo: MainRequestsRepo, **_kwargs
) -> dict[str, Any]:
    """Геттер для управления доступом к казино группы.

    Args:
        user: Экземпляр пользователя с моделью Employee (руководитель)
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь с информацией о доступе к казино для каждого члена группы
    """
    # Получаем всех пользователей группы
    group_members = await stp_repo.employee.get_users(head=user.fullname)

    if not group_members:
        return {
            "members": [],
            "total_members": 0,
            "casino_enabled_count": 0,
        }

    # Сортируем по ФИО
    sorted_members = sorted(group_members, key=lambda k: k.fullname)

    # Форматируем для отображения
    formatted_members = []
    casino_enabled_count = 0

    for member in sorted_members:
        if member.is_casino_allowed:
            casino_enabled_count += 1

        status_emoji = "🟢" if member.is_casino_allowed else "🔴"
        member_name = format_fullname(member.fullname, True, True)

        formatted_members.append((
            member.id,
            f"{status_emoji} {member_name}",
            member.is_casino_allowed,
        ))

    return {
        "members": formatted_members,
        "total_members": len(sorted_members),
        "casino_enabled_count": casino_enabled_count,
    }


async def game_rating_getter(
    user: Employee, stp_repo: MainRequestsRepo, **_kwargs
) -> dict[str, Any]:
    """Геттер для получения рейтинга группы по балансу.

    Args:
        user: Экземпляр пользователя с моделью Employee (руководитель)
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь с рейтингом группы по балансу
    """
    # Получаем всех пользователей группы
    group_members = await stp_repo.employee.get_users(head=user.fullname)

    if not group_members:
        return {
            "rating_text": "❌ В твоей группе нет сотрудников",
            "members": [],
        }

    # Получаем балансы для всех членов группы
    members_with_balance = []
    for member in group_members:
        balance = await stp_repo.transaction.get_user_balance(member.user_id)
        members_with_balance.append((member, balance))

    # Сортируем по балансу (убывание)
    sorted_members = sorted(members_with_balance, key=lambda x: x[1], reverse=True)

    # Форматируем рейтинг
    rating_lines = ["🎖️ <b>Рейтинг группы по балансу</b>\n"]

    medals = ["🥇", "🥈", "🥉"]
    for idx, (member, balance) in enumerate(sorted_members, 1):
        if idx <= 3:
            prefix = medals[idx - 1]
        else:
            prefix = f"{idx}."

        member_name = format_fullname(
            member.fullname, True, True, member.username, member.user_id
        )
        rating_lines.append(f"{prefix} {member_name}")
        rating_lines.append(f"{balance} баллов")

    rating_text = "\n".join(rating_lines)

    return {
        "rating_text": rating_text,
        "members": [(m[0].id, m[0].fullname, m[1]) for m in sorted_members],
    }

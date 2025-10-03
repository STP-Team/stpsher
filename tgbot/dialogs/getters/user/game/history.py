"""Геттеры для меню истории баланса."""

from typing import Any, Dict

from aiogram_dialog import DialogManager

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo


async def history_getter(
    user: Employee, stp_repo: MainRequestsRepo, **_kwargs
) -> Dict[str, Any]:
    """Геттер для получения истории транзакций пользователя.

    Args:
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP

    Returns:
        Словарь с информацией о транзакциях пользователя
    """
    user_transactions = await stp_repo.transaction.get_user_transactions(
        user_id=user.user_id
    )

    total_transactions = len(user_transactions)

    formatted_transactions = []
    for transaction in user_transactions:
        # Определяем эмодзи и текст типа операции
        type_emoji = "➕" if transaction.type == "earn" else "➖"
        type_text = "Начисление" if transaction.type == "earn" else "Списание"

        # Определяем источник транзакции
        source_names = {
            "achievement": "🏆",
            "product": "🛒",
            "manual": "✍️",
            "casino": "🎰",
        }
        source_icon = source_names.get(transaction.source_type, "❓")

        date_str = transaction.created_at.strftime("%d.%m.%y")
        button_text = f"{type_emoji} {transaction.amount} {source_icon} ({date_str})"

        formatted_transactions.append(
            (
                transaction.id,  # ID для обработчика клика
                button_text,  # Текст кнопки
                transaction.amount,  # Сумма
                type_text,  # Тип операции (текст)
                source_icon,  # Иконка источника
                date_str,  # Дата
                transaction.type,  # Тип операции (earn/spend)
                transaction.source_type,  # Тип источника
                transaction.comment or "",  # Комментарий
                transaction.created_at.strftime("%d.%m.%Y в %H:%M"),  # Полная дата
            )
        )

    return {
        "history_products": formatted_transactions,
        "total_transactions": total_transactions,
    }


async def history_detail_getter(
    dialog_manager: DialogManager, stp_repo: MainRequestsRepo, **_kwargs
) -> Dict[str, Any]:
    """Геттер информации для детального просмотра транзакции.

    Args:
        stp_repo: Репозиторий операций с базой STP
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с деталями выбранной транзакции пользователя
    """
    transaction_info = dialog_manager.dialog_data.get("selected_transaction")

    if not transaction_info:
        return {}

    # Определяем эмодзи и текст типа операции
    type_emoji = "➕" if transaction_info["type"] == "earn" else "➖"
    type_text = "Начисление" if transaction_info["type"] == "earn" else "Списание"

    # Определяем источник транзакции
    source_names = {
        "achievement": "🏆 Достижение",
        "product": "🛒 Покупка предмета",
        "manual": "✍️ Ручная операция",
        "casino": "🎰 Казино",
    }
    source_name = source_names.get(transaction_info["source_type"], "❓ Неизвестно")

    # Дополнительная информация для достижений
    if (
        transaction_info["source_type"] == "achievement"
        and transaction_info["source_id"]
    ):
        try:
            achievement = await stp_repo.achievement.get_achievement(
                transaction_info["source_id"]
            )
            if achievement:
                match achievement.period:
                    case "d":
                        source_name = "🏆 Ежедневное достижение: " + achievement.name
                    case "w":
                        source_name = "🏆 Еженедельное достижение: " + achievement.name
                    case "m":
                        source_name = "🏆 Ежемесячное достижение: " + achievement.name
        except Exception:
            # Если не удалось получить информацию о достижении, оставляем базовое название
            pass

    return {
        "transaction_id": transaction_info["id"],
        "type_emoji": type_emoji,
        "type_text": type_text,
        "amount": transaction_info["amount"],
        "source_name": source_name,
        "created_at": transaction_info["created_at"],
        "comment": transaction_info["comment"],
    }

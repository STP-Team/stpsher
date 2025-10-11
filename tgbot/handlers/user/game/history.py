import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from stp_database.repo.STP.requests import MainRequestsRepo

from tgbot.keyboards.user.game.history import (
    TransactionDetailMenu,
    TransactionHistoryMenu,
    transaction_detail_kb,
    transaction_history_kb,
)
from tgbot.keyboards.user.game.main import GameMenu

user_game_history_router = Router()
user_game_history_router.message.filter(
    F.chat.type == "private",
)
user_game_history_router.callback_query.filter(F.message.chat.type == "private")

logger = logging.getLogger(__name__)


@user_game_history_router.callback_query(GameMenu.filter(F.menu == "history"))
async def game_history(callback: CallbackQuery, stp_repo: MainRequestsRepo):
    """Показывает историю транзакций пользователя"""
    user_transactions = await stp_repo.transaction.get_user_transactions(
        user_id=callback.from_user.id
    )

    if not user_transactions:
        await callback.message.edit_text(
            """📜 <b>История баланса</b>

Здесь отображается вся история операций с баллами

У тебя пока нет транзакций 🙂

<i>Транзакции появляются при покупке предметов, получении достижений и других операциях с баллами</i>""",
            reply_markup=transaction_history_kb([], current_page=1),
        )
        return

    # Показываем первую страницу по умолчанию
    total_transactions = len(user_transactions)

    message_text = f"""📜 <b>История баланса</b>

Здесь отображается вся история операций с баллами

<i>Всего транзакций: {total_transactions}</i>"""

    await callback.message.edit_text(
        message_text,
        reply_markup=transaction_history_kb(user_transactions, current_page=1),
    )


@user_game_history_router.callback_query(
    TransactionHistoryMenu.filter(F.menu == "history")
)
async def game_history_paginated(
    callback: CallbackQuery,
    callback_data: TransactionHistoryMenu,
    stp_repo: MainRequestsRepo,
):
    """Обработчик пагинации истории транзакций"""
    page = callback_data.page

    user_transactions = await stp_repo.transaction.get_user_transactions(
        user_id=callback.from_user.id
    )

    if not user_transactions:
        await callback.message.edit_text(
            """📜 <b>История баланса</b>

Здесь отображается вся история операций с баллами

У тебя пока нет транзакций 🙂

<i>Транзакции появляются при покупке предметов, получении достижений и других операциях с баллами</i>""",
            reply_markup=transaction_history_kb([], current_page=1),
        )
        return

    total_transactions = len(user_transactions)

    message_text = f"""📜 <b>История баланса</b>

Здесь отображается вся история операций с баллами

<i>Всего транзакций: {total_transactions}</i>"""

    await callback.message.edit_text(
        message_text,
        reply_markup=transaction_history_kb(user_transactions, current_page=page),
    )


@user_game_history_router.callback_query(TransactionDetailMenu.filter())
async def transaction_detail_view(
    callback: CallbackQuery,
    callback_data: TransactionDetailMenu,
    stp_repo: MainRequestsRepo,
):
    """Обработчик детального просмотра транзакции"""
    transaction_id = callback_data.transaction_id
    page = callback_data.page

    # Получаем информацию о транзакции
    transaction = await stp_repo.transaction.get_transaction(transaction_id)

    if not transaction:
        await callback.message.edit_text(
            """📜 <b>История баланса</b>

Не смог найти информацию о транзакции ☹""",
            reply_markup=transaction_detail_kb(page),
        )
        return

    # Определяем эмодзи и текст типа операции
    type_emoji = "➕" if transaction.type == "earn" else "➖"
    type_text = "Начисление" if transaction.type == "earn" else "Списание"

    # Определяем источник транзакции
    source_names = {
        "achievement": "🏆 Достижение",
        "product": "🛒 Покупка предмета",
        "manual": "✍️ Ручная операция",
        "casino": "🎰 Казино",
    }
    source_name = source_names.get(transaction.source_type, "❓ Неизвестно")
    if transaction.source_type == "achievement" and transaction.source_id:
        achievement = await stp_repo.achievement.get_achievement(transaction.source_id)
        match achievement.period:
            case "d":
                source_name = "🏆 Ежедневное достижение: " + achievement.name
            case "w":
                source_name = "🏆 Еженедельное достижение: " + achievement.name
            case "m":
                source_name = "🏆 Ежемесячное достижение: " + achievement.name

    # Формируем сообщение с подробной информацией
    message_text = f"""<b>📊 Детали транзакции</b>

<b>📈 Операция</b>
{type_emoji} {type_text} <b>{transaction.amount}</b> баллов

<b>🔢 ID:</b> <code>{transaction.id}</code>

<b>📍 Источник</b>
{source_name}

<b>📅 Дата создания</b>
{transaction.created_at.strftime("%d.%m.%Y в %H:%M")}"""

    if transaction.comment:
        message_text += f"\n\n<b>💬 Комментарий</b>\n<blockquote expandable>{transaction.comment}</blockquote>"

    await callback.message.edit_text(
        message_text, reply_markup=transaction_detail_kb(page)
    )

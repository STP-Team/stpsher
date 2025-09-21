import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import HeadFilter
from tgbot.keyboards.head.group.game.history import (
    HeadGroupHistoryMenu,
    HeadTransactionDetailMenu,
    head_group_history_kb,
    head_transaction_detail_kb,
)
from tgbot.keyboards.head.group.game.main import HeadGameMenu

head_game_history_router = Router()
head_game_history_router.callback_query.filter(
    F.message.chat.type == "private", HeadFilter()
)

logger = logging.getLogger(__name__)


@head_game_history_router.callback_query(HeadGameMenu.filter(F.menu == "history"))
async def head_group_history(
    callback: CallbackQuery,
    callback_data: HeadGroupHistoryMenu,
    user: Employee,
    stp_repo: MainRequestsRepo,
):
    if not user:
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\nНе удалось найти информацию в базе данных."
        )
        return

    # Получаем транзакции группы
    group_transactions = await stp_repo.transaction.get_group_transactions(
        user.fullname
    )

    group_members_result = await stp_repo.session.execute(
        select(Employee).where(Employee.head == user.fullname)
    )
    members = group_members_result.scalars().all()
    employee_names = {
        member.user_id: member.fullname for member in members if member.user_id
    }

    page = callback_data.page

    if not group_transactions:
        await callback.message.edit_text(
            """📜 <b>История баланса группы</b>

Здесь отображается вся история операций с баллами всех участников вашей группы

У группы пока нет транзакций 🙂

<i>Транзакции появляются при покупке предметов участниками, получении достижений и других операциях с баллами</i>""",
            reply_markup=head_group_history_kb(
                [], current_page=page, employee_names=employee_names
            ),
        )
        return

    total_transactions = len(group_transactions)

    message_text = f"""📜 <b>История баланса группы</b>

Здесь отображается вся история операций с баллами всех участников вашей группы

<i>Всего транзакций: {total_transactions}</i>"""

    await callback.message.edit_text(
        message_text,
        reply_markup=head_group_history_kb(
            group_transactions, current_page=page, employee_names=employee_names
        ),
    )

    logger.info(
        f"[Руководитель] - [История группы] {callback.from_user.username} ({callback.from_user.id}): Просмотр истории группы, страница {page}"
    )


@head_game_history_router.callback_query(HeadTransactionDetailMenu.filter())
async def head_transaction_detail_view(
    callback: CallbackQuery,
    callback_data: HeadTransactionDetailMenu,
    stp_repo: MainRequestsRepo,
):
    """Обработчик детального просмотра транзакции группы"""
    transaction_id = callback_data.transaction_id
    page = callback_data.page

    # Получаем информацию о транзакции
    transaction = await stp_repo.transaction.get_transaction(transaction_id)

    if not transaction:
        await callback.message.edit_text(
            """📜 <b>История баланса группы</b>

Не смог найти информацию о транзакции ☹""",
            reply_markup=head_transaction_detail_kb(page),
        )
        return

    # Получаем информацию о сотруднике
    employee = await stp_repo.employee.get_user(user_id=transaction.user_id)

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
    message_text = f"""<b>📊 Детали транзакции группы</b>

<b>👤 Сотрудник</b>
<a href='t.me/{employee.username}'>{employee.fullname}</a>

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
        message_text, reply_markup=head_transaction_detail_kb(page)
    )

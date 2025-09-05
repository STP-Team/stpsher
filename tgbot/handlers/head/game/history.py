import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import HeadFilter
from tgbot.keyboards.head.group.game.history import (
    HeadGroupHistoryMenu,
    HeadRankingMenu,
    HeadTransactionDetailMenu,
    head_group_history_kb,
    head_ranking_kb,
    head_transaction_detail_kb,
)
from tgbot.keyboards.head.group.members import short_name

head_game_history_router = Router()
head_game_history_router.callback_query.filter(
    F.message.chat.type == "private", HeadFilter()
)

logger = logging.getLogger(__name__)


@head_game_history_router.callback_query(
    HeadGroupHistoryMenu.filter(F.menu == "history")
)
async def head_group_history(
    callback: CallbackQuery,
    callback_data: HeadGroupHistoryMenu,
    stp_repo: MainRequestsRepo,
):
    """Показывает историю транзакций группы для руководителя"""
    current_user = await stp_repo.employee.get_user(user_id=callback.from_user.id)

    if not current_user:
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\nНе удалось найти вашу информацию в базе данных."
        )
        return

    # Получаем транзакции группы
    group_transactions = await stp_repo.transaction.get_group_transactions(
        current_user.fullname
    )

    # Получаем информацию о сотрудниках для отображения их имен
    from sqlalchemy import select

    from infrastructure.database.models.STP.employee import Employee

    group_members_result = await stp_repo.session.execute(
        select(Employee).where(Employee.head == current_user.fullname)
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
    employee_name = employee.fullname if employee else "Неизвестный сотрудник"

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

    # Формируем сообщение с подробной информацией
    message_text = f"""<b>📊 Детали транзакции группы</b>

<b>👤 Сотрудник</b>
{employee_name}

<b>📈 Операция</b>
{type_emoji} {type_text} <b>{transaction.amount}</b> баллов

<b>🔢 ID:</b> <code>{transaction.id}</code>

<b>📍 Источник</b>
{source_name}

<b>📅 Дата создания</b>
{transaction.created_at.strftime("%d.%m.%Y в %H:%M")}"""

    if transaction.comment:
        message_text += f"\n\n<b>💬 Комментарий</b>\n<blockquote expandable>{transaction.comment}</blockquote>"

    if transaction.source_id:
        message_text += f"\n\n<b>🔗 ID источника</b>\n└ {transaction.source_id}"

    await callback.message.edit_text(
        message_text, reply_markup=head_transaction_detail_kb(page)
    )


@head_game_history_router.callback_query(HeadRankingMenu.filter(F.menu == "ranking"))
async def head_ranking_view(callback: CallbackQuery, stp_repo: MainRequestsRepo):
    """Показывает рейтинг руководителей по дивизиону"""
    current_user = await stp_repo.employee.get_user(user_id=callback.from_user.id)

    if not current_user:
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\nНе удалось найти вашу информацию в базе данных."
        )
        return

    if not current_user.division:
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\nУ вас не указан дивизион в базе данных.",
            reply_markup=head_ranking_kb(),
        )
        return

    # Получаем рейтинг руководителей по дивизиону
    ranking = await stp_repo.transaction.get_heads_ranking_by_division(
        current_user.division
    )

    if not ranking:
        await callback.message.edit_text(
            f"""📊 <b>Рейтинг {current_user.division}</b>

В твоем направлении пока нет данных о других руководителях или активности за текущий месяц

<i>Рейтинг обновляется в реальном времени на основе суммы баллов групп за текущий месяц</i>""",
            reply_markup=head_ranking_kb(),
        )
        return

    # Формируем текст с рейтингом
    months_ru = {
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
    current_month_name = f"{months_ru[datetime.now().month]} {datetime.now().year}"

    message_text = f"""📊 <b>Рейтинг ({current_user.division})</b>

<b>🏆 Места за {current_month_name}:</b>

"""

    # Определяем место текущего пользователя
    current_user_place = None
    for head_data in ranking:
        if head_data["head_name"] == current_user.fullname:
            current_user_place = head_data["place"]
            break

    # Показываем топ-10
    display_ranking = ranking[:10]

    for i, head_data in enumerate(display_ranking):
        place_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{head_data['place']}."

        # Форматируем имя
        name_display = short_name(head_data["head_name"])
        if len(name_display) > 25:
            name_display = name_display[:22] + "..."

        message_text += (
            f"{place_emoji} <a href='t.me/{head_data['username']}'>{name_display}</a>\n"
        )
        message_text += (
            f"Группа: {head_data['group_size']} чел. • {head_data['points']} баллов\n\n"
        )

    if current_user_place:
        if current_user_place > 10:
            message_text += (
                f"...\n\n<b>Твое место: {current_user_place} из {len(ranking)}</b>"
            )
        else:
            message_text += f"<b>Всего руководителей: {len(ranking)}</b>"
    else:
        message_text += f"<b>Всего руководителей: {len(ranking)}</b>"

    await callback.message.edit_text(
        message_text, reply_markup=head_ranking_kb(), parse_mode="HTML"
    )

    logger.info(
        f"[Руководитель] - [Рейтинг] {callback.from_user.username} ({callback.from_user.id}): Просмотр рейтинга руководителей {current_user.division}"
    )

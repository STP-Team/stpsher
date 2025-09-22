import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import HeadFilter
from tgbot.keyboards.head.group.game.main import HeadGameMenu
from tgbot.keyboards.head.group.game.rating import game_balance_rating_kb
from tgbot.keyboards.head.group.members import short_name

head_group_game_rating_router = Router()
head_group_game_rating_router.message.filter(F.chat.type == "private", HeadFilter())
head_group_game_rating_router.callback_query.filter(
    F.message.chat.type == "private", HeadFilter()
)

logger = logging.getLogger(__name__)


async def format_balance_rating_message(
    group_members, stp_repo: MainRequestsRepo
) -> str:
    """Форматирует сообщение с рейтингом группы по балансу"""

    # Собираем данные о балансе для всех участников группы
    balance_data = []

    for member in group_members:
        if member.user_id:  # Проверяем, что у пользователя есть user_id
            balance = await stp_repo.transaction.get_user_balance(member.user_id)
            balance_data.append({"member": member, "balance": balance})

    # Сортируем по балансу (больше = лучше)
    balance_data.sort(key=lambda x: x["balance"], reverse=True)

    # Формируем сообщение
    message = "🎖️ <b>Рейтинг группы по балансу</b>\n\n"

    if not balance_data:
        message += "<i>Нет данных о балансе участников</i>"
    else:
        for i, data in enumerate(balance_data, 1):
            member = data["member"]
            balance = data["balance"]

            # Эмодзи для позиций
            if i == 1:
                position_emoji = "🥇"
            elif i == 2:
                position_emoji = "🥈"
            elif i == 3:
                position_emoji = "🥉"
            else:
                position_emoji = f"{i}."

            # Формируем строку рейтинга
            if member.username:
                member_link = f"<a href='t.me/{member.username}'>{short_name(member.fullname)}</a>"
            else:
                member_link = short_name(member.fullname)

            message += f"{position_emoji} <b>{member_link}</b>\n"
            message += f"{balance} баллов\n"

    return message


@head_group_game_rating_router.callback_query(HeadGameMenu.filter(F.menu == "rating"))
async def group_balance_rating_cb(
    callback: CallbackQuery,
    user: Employee,
    stp_repo: MainRequestsRepo,
):
    """Обработчик рейтинга группы по балансу"""
    if not user:
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\nНе удалось найти информацию в базе данных."
        )
        return

    # Получаем всех сотрудников этого руководителя
    group_members = await stp_repo.employee.get_users_by_head(user.fullname)

    if not group_members:
        await callback.message.edit_text(
            "🎖️ <b>Рейтинг группы по балансу</b>\n\nУ тебя пока нет подчиненных в системе\n\n<i>Если это ошибка, обратись к администратору.</i>",
            reply_markup=game_balance_rating_kb(),
        )
        return

    try:
        # Формируем сообщение с рейтингом
        message_text = await format_balance_rating_message(group_members, stp_repo)

        await callback.message.edit_text(
            message_text,
            reply_markup=game_balance_rating_kb(),
        )

        logger.info(
            f"[Руководитель] - [Рейтинг баланса] {callback.from_user.username} ({callback.from_user.id}): Открыт рейтинг группы по балансу"
        )

    except TelegramBadRequest:
        await callback.answer("Обновлений нет")
    except Exception as e:
        logger.error(f"Ошибка при получении рейтинга группы по балансу: {e}")
        await callback.answer(
            "❌ Ошибка при получении данных рейтинга", show_alert=True
        )

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    ChatMemberAdministrator,
    ChatMemberOwner,
    Message,
)
from stp_database import Employee, MainRequestsRepo

from tgbot.filters.role import DutyFilter, MultiRoleFilter, SpecialistFilter
from tgbot.misc.helpers import format_fullname
from tgbot.services.leveling import LevelingSystem

logger = logging.getLogger(__name__)

group_user_router = Router()
group_user_router.message.filter(F.chat.type.in_(("groups", "supergroup")))


@group_user_router.message(Command("admins"))
async def admins_cmd(
    message: Message, user: Employee, stp_repo: MainRequestsRepo
) -> None:
    """Обработчик команды /admins для групп.

    Args:
        message: Сообщение от пользователя
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
    """
    try:
        chat_administrators = await message.bot.get_chat_administrators(message.chat.id)

        admin_list = []
        owner = None

        for admin in chat_administrators:
            user_info = admin.user

            db_user = await stp_repo.employee.get_users(user_id=user_info.id)
            if db_user:
                display_name = format_fullname(db_user, True, True)
            else:
                display_name = (
                    f"@{user_info.username}"
                    if user_info.username
                    else user_info.full_name
                )

            if isinstance(admin, ChatMemberOwner):
                owner = display_name
            elif isinstance(admin, ChatMemberAdministrator):
                admin_list.append(display_name)

        # Формируем сообщение
        message_parts = ["<b>Администраторы группы:</b>"]

        # Добавляем владельца
        if owner:
            message_parts.append(f"- {owner}, владелец")

        # Добавляем администраторов
        for admin_name in admin_list:
            message_parts.append(f"- {admin_name}")

        # Если нет администраторов
        if not admin_list and not owner:
            message_parts.append("Администраторы не найдены")

        response_text = "\n".join(message_parts)

        await message.reply(response_text)

        # Логируем использование команды
        logger.info(
            f"[/admins] {user.fullname} ({message.from_user.id}) запросил список администраторов группы {message.chat.id}"
        )

    except Exception as e:
        logger.error(f"Ошибка при получении списка администраторов: {e}")
        await message.reply(
            "🚨 Не смог найти администраторов. Возможно, у меня недостаточно прав"
        )


@group_user_router.message(
    Command("balance"), MultiRoleFilter(SpecialistFilter(), DutyFilter())
)
async def balance_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """Обработчик команды /balance для групп.

    Args:
        message: Сообщение от пользователя
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
    """
    try:
        user_balance = await stp_repo.transaction.get_user_balance(user_id=user.user_id)
        achievements_sum = await stp_repo.transaction.get_user_achievements_sum(
            user_id=user.user_id
        )
        level_info_text = LevelingSystem.get_level_info_text(
            achievements_sum, user_balance
        )

        await message.reply(level_info_text)

        # Логируем использование команды
        logger.info(
            f"[/balance] {user.fullname} ({message.from_user.id}) запросил свой баланс"
        )

    except Exception as e:
        logger.error(f"Ошибка при получении баланса: {e}")
        await message.reply("🚨 Не смог получить твой баланс. Напиши в @stp_helpbot")


@group_user_router.message(Command("top"))
async def top_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """Обработчик команды /top для групп.

    Args:
        message: Сообщение от пользователя
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
    """
    try:
        # Получаем участников группы из базы
        group_members_data = await stp_repo.group_member.get_group_members(
            message.chat.id
        )

        if not group_members_data:
            await message.reply(
                "🎖️ <b>Рейтинг группы по баллам</b>\n\n<i>Нет участников в базе для этой группы</i>"
            )
            return

        # Получаем информацию о сотрудниках и их балансах
        balance_data = []

        for member_data in group_members_data:
            # Получаем информацию о сотруднике по member_id
            employee = await stp_repo.employee.get_users(user_id=member_data.member_id)
            if employee and employee.user_id:
                balance = await stp_repo.transaction.get_user_balance(employee.user_id)
                balance_data.append({"employee": employee, "balance": balance})

        # Сортируем по балансу (больше = лучше)
        balance_data.sort(key=lambda x: x["balance"], reverse=True)

        # Формируем сообщение
        message_text = "🎖️ <b>Рейтинг группы по баллам</b>\n\n"

        if not balance_data:
            message_text += "<i>Нет данных о балансе участников</i>"
        else:
            for i, data in enumerate(balance_data, 1):
                employee = data["employee"]
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
                employee_link = format_fullname(employee, True, True)

                message_text += f"{position_emoji} <b>{employee_link}</b>\n"
                message_text += f"{balance} баллов\n"

        await message.reply(message_text)

        # Логируем использование команды
        logger.info(
            f"[/top] {user.fullname} ({message.from_user.id}) запросил рейтинг группы {message.chat.id}"
        )

    except Exception as e:
        logger.error(f"Ошибка при получении рейтинга группы: {e}")
        await message.reply(
            "🚨 Не смог посчитать рейтинг группы. Напиши в @stp_helpbot"
        )

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    ChatMemberAdministrator,
    ChatMemberOwner,
    Message,
)

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import DutyFilter, MultiRoleFilter, SpecialistFilter
from tgbot.keyboards.group import short_name
from tgbot.services.leveling import LevelingSystem

logger = logging.getLogger(__name__)

group_user_router = Router()
group_user_router.message.filter(F.chat.type.in_(("group", "supergroup")))


@group_user_router.message(Command("admins"))
async def admins_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """/admins для получения списка администраторов группы"""
    try:
        # Получаем список администраторов чата
        chat_administrators = await message.bot.get_chat_administrators(message.chat.id)

        # Обрабатываем каждого администратора и проверяем их в базе данных
        admin_list = []
        owner = None

        for admin in chat_administrators:
            user_info = admin.user

            # Проверяем администратора в базе данных
            db_user = await stp_repo.employee.get_user(user_id=user_info.id)
            if db_user:
                # Если есть в БД, используем данные из БД с ссылкой
                if db_user.username:
                    display_name = f"<a href='t.me/{db_user.username}'>{short_name(db_user.fullname)}</a>"
                else:
                    display_name = short_name(db_user.fullname)
            else:
                # Если нет в БД, используем данные из Telegram
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
            "❌ Произошла ошибка при получении списка администраторов. Возможно, у бота недостаточно прав."
        )


@group_user_router.message(
    Command("balance"), MultiRoleFilter(SpecialistFilter(), DutyFilter())
)
async def balance_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """/balance для получения своего баланса"""
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
        await message.reply("❌ Произошла ошибка при получении баланса")


@group_user_router.message(Command("top"))
async def top_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """/top для получения рейтинга группы"""
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
            employee = await stp_repo.employee.get_user(user_id=member_data.member_id)
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
                if employee.username:
                    employee_link = f"<a href='t.me/{employee.username}'>{short_name(employee.fullname)}</a>"
                else:
                    employee_link = short_name(employee.fullname)

                message_text += f"{position_emoji} <b>{employee_link}</b>\n"
                message_text += f"{balance} баллов\n"

        await message.reply(message_text)

        # Логируем использование команды
        logger.info(
            f"[/top] {user.fullname} ({message.from_user.id}) запросил рейтинг группы {message.chat.id}"
        )

    except Exception as e:
        logger.error(f"Ошибка при получении рейтинга группы: {e}")
        await message.reply("❌ Произошла ошибка при получении рейтинга группы")

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner, Message

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.group import GroupAdminFilter
from tgbot.keyboards.mip.search import short_name

logger = logging.getLogger(__name__)

group_admin_router = Router()
group_admin_router.message.filter(F.chat.type.in_(("group", "supergroup")))


@group_admin_router.message(Command("admins"))
async def admins_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """/admins для получения списка администраторов группы"""

    # Проверяем авторизацию пользователя
    if not user:
        await message.reply(
            "❌ Для использования команды /admins необходимо авторизоваться в боте"
        )
        return

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


@group_admin_router.message(Command("pin"), GroupAdminFilter())
async def pin_cmd(message: Message, user: Employee):
    """/pin для закрепления сообщения"""

    # Проверяем авторизацию пользователя
    if not user:
        await message.reply(
            "❌ Для использования команды /pin необходимо авторизоваться в боте"
        )
        return

    # Проверяем, что команда используется в ответ на сообщение
    if not message.reply_to_message:
        await message.reply(
            "❌ Для закрепления используй команду /pin в ответ на сообщение, которое нужно закрепить"
        )
        return

    try:
        # Закрепляем сообщение
        await message.bot.pin_chat_message(
            chat_id=message.chat.id,
            message_id=message.reply_to_message.message_id,
            disable_notification=True,
        )

        # Формируем ссылку на закрепленное сообщение
        chat_id_str = str(message.chat.id).replace("-100", "")
        message_link = f"t.me/c/{chat_id_str}/{message.reply_to_message.message_id}"
        await message.reply(f"✅ Закрепил <a href='{message_link}'>сообщение</a>")

        # Логируем использование команды
        logger.info(
            f"[/pin] {user.fullname} ({message.from_user.id}) закрепил сообщение в группе {message.chat.id}"
        )

    except Exception as e:
        logger.error(f"Ошибка при закреплении сообщения: {e}")
        await message.reply(
            "❌ Произошла ошибка при закреплении сообщения. Возможно, у бота недостаточно прав."
        )


@group_admin_router.message(Command("unpin"), GroupAdminFilter())
async def unpin_cmd(message: Message, user: Employee):
    """/unpin для открепления сообщения"""

    # Проверяем авторизацию пользователя
    if not user:
        await message.reply(
            "❌ Для использования команды /unpin необходимо авторизоваться в боте"
        )
        return

    # Проверяем, что команда используется в ответ на сообщение
    if not message.reply_to_message:
        await message.reply(
            "❌ Для открепления используй команду /unpin в ответ на закрепленное сообщение, которое нужно открепить"
        )
        return

    try:
        # Открепляем конкретное сообщение
        await message.bot.unpin_chat_message(
            chat_id=message.chat.id, message_id=message.reply_to_message.message_id
        )

        await message.reply("✅ Сообщение откреплено")

        # Логируем использование команды
        logger.info(
            f"[/unpin] {user.fullname} ({message.from_user.id}) открепил сообщение в группе {message.chat.id}"
        )

    except Exception as e:
        logger.error(f"Ошибка при откреплении сообщения: {e}")
        await message.reply(
            "❌ Произошла ошибка при откреплении сообщения. Возможно, у бота недостаточно прав."
        )

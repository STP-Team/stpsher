import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    ChatMemberAdministrator,
    ChatMemberOwner,
    ChatPermissions,
    Message,
)

from infrastructure.database.models import Employee
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.group import GroupAdminFilter
from tgbot.keyboards.mip.search import short_name

logger = logging.getLogger(__name__)

group_admin_router = Router()
group_admin_router.message.filter(F.chat.type.in_(("group", "supergroup")))


def parse_duration(duration_str: str) -> Optional[timedelta]:
    """
    Парсит строку длительности в timedelta
    Поддерживает форматы: 1h, 30m, 7d, 1ч, 30м, 7д
    """
    if not duration_str:
        return None

    # Паттерны для английского и русского языков
    patterns = [
        (r"^(\d+)h$", "hours"),  # 1h
        (r"^(\d+)m$", "minutes"),  # 30m
        (r"^(\d+)d$", "days"),  # 7d
        (r"^(\d+)ч$", "hours"),  # 1ч
        (r"^(\d+)м$", "minutes"),  # 30м
        (r"^(\d+)д$", "days"),  # 7д
    ]

    for pattern, unit in patterns:
        match = re.match(pattern, duration_str.lower())
        if match:
            value = int(match.group(1))
            if unit == "minutes":
                return timedelta(minutes=value)
            elif unit == "hours":
                return timedelta(hours=value)
            elif unit == "days":
                return timedelta(days=value)

    return None


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


@group_admin_router.message(Command("mute"), GroupAdminFilter())
async def mute_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """/mute для заглушения пользователя"""

    # Проверяем авторизацию пользователя
    if not user:
        await message.reply(
            "❌ Для использования команды /mute необходимо авторизоваться в боте"
        )
        return

    target_user_id = None
    target_user_name = "Пользователь"
    duration = None
    unmute_at = None

    # Парсим аргументы команды
    command_args = message.text.split()[1:] if message.text else []

    # Проверяем способы указания пользователя
    if message.reply_to_message:
        # Заглушение через ответ на сообщение
        target_user_id = message.reply_to_message.from_user.id
        target_user_name = (
            message.reply_to_message.from_user.full_name or f"#{target_user_id}"
        )

        # Проверяем наличие длительности в аргументах
        if command_args:
            duration_str = command_args[0]
            duration = parse_duration(duration_str)
            if duration is None and duration_str:
                await message.reply(
                    "❌ Неверный формат времени. Используй формат: 1h, 30m, 7d, 1ч, 30м, 7д или оставь пустым для постоянного мьюта"
                )
                return
    else:
        # Заглушение по user_id из текста команды
        if not command_args:
            await message.reply(
                "❌ Укажи user_id или используй команду в ответ на сообщение пользователя, которого хочешь заглушить"
            )
            return

        # Первый аргумент - user_id
        try:
            target_user_id = int(command_args[0])
        except ValueError:
            await message.reply(
                "❌ Неверный формат user_id. Используй команду /mute <user_id> [время] или ответь на сообщение пользователя"
            )
            return

        # Второй аргумент - длительность (если есть)
        if len(command_args) > 1:
            duration_str = command_args[1]
            duration = parse_duration(duration_str)
            if duration is None:
                await message.reply(
                    "❌ Неверный формат времени. Используй формат: 1h, 30m, 7d, 1ч, 30м, 7д или оставь пустым для постоянного мьюта"
                )
                return

    # Если указана длительность, вычисляем время размута
    if duration:
        unmute_at = datetime.utcnow() + duration

    try:
        # Используем chat_restrict для ограничения пользователя в Telegram
        restricted_permissions = ChatPermissions(
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
        )

        await message.bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_user_id,
            permissions=restricted_permissions,
            until_date=unmute_at,
        )

        # Получаем информацию о заглушенном пользователе для красивого отображения
        employee = await stp_repo.employee.get_user(user_id=target_user_id)
        if employee:
            display_name = short_name(employee.fullname)
        else:
            display_name = target_user_name

        # Формируем сообщение с информацией о мьюте
        if duration:
            if duration.days > 0:
                duration_text = f"{duration.days} дн."
            elif duration.seconds >= 3600:
                duration_text = f"{duration.seconds // 3600} ч."
            else:
                duration_text = f"{duration.seconds // 60} мин."
            mute_message = (
                f"🔇 Пользователь {display_name} заглушен в группе на {duration_text}"
            )
        else:
            mute_message = f"🔇 Пользователь {display_name} заглушен в группе навсегда"

        await message.reply(mute_message)

        # Логируем использование команды
        duration_log = f" на {duration}" if duration else " навсегда"
        logger.info(
            f"[/mute] {user.fullname} ({message.from_user.id}) заглушил пользователя {target_user_id} в группе {message.chat.id}{duration_log}"
        )

    except Exception as e:
        logger.error(f"Ошибка при заглушении пользователя: {e}")
        await message.reply("❌ Произошла ошибка при заглушении пользователя")


@group_admin_router.message(Command("unmute"), GroupAdminFilter())
async def unmute_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """/unmute для разглушения пользователя"""

    # Проверяем авторизацию пользователя
    if not user:
        await message.reply(
            "❌ Для использования команды /unmute необходимо авторизоваться в боте"
        )
        return

    target_user_id = None
    target_user_name = "Пользователь"

    # Проверяем способы указания пользователя
    if message.reply_to_message:
        # Разглушение через ответ на сообщение
        target_user_id = message.reply_to_message.from_user.id
        target_user_name = (
            message.reply_to_message.from_user.full_name or f"#{target_user_id}"
        )
    else:
        # Разглушение по user_id из текста команды
        command_args = message.text.split()[1:] if message.text else []
        if command_args:
            try:
                target_user_id = int(command_args[0])
            except ValueError:
                await message.reply(
                    "❌ Неверный формат user_id. Используй команду /unmute <user_id> или ответь на сообщение пользователя"
                )
                return
        else:
            await message.reply(
                "❌ Укажи user_id или используй команду в ответ на сообщение пользователя, которого хочешь разглушить"
            )
            return

    try:
        # Восстанавливаем права пользователя в Telegram
        normal_permissions = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
        )

        await message.bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_user_id,
            permissions=normal_permissions,
        )

        # Получаем информацию о разглушенном пользователе для красивого отображения
        employee = await stp_repo.employee.get_user(user_id=target_user_id)
        if employee:
            display_name = short_name(employee.fullname)
        else:
            display_name = target_user_name

        await message.reply(f"🔊 Пользователь {display_name} разглушен в группе")

        # Логируем использование команды
        logger.info(
            f"[/unmute] {user.fullname} ({message.from_user.id}) разглушил пользователя {target_user_id} в группе {message.chat.id}"
        )

    except Exception as e:
        logger.error(f"Ошибка при разглушении пользователя: {e}")
        await message.reply("❌ Произошла ошибка при разглушении пользователя")

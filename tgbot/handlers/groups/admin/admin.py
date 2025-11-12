import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    ChatPermissions,
    Message,
)
from stp_database import Employee, MainRequestsRepo

from tgbot.filters.group import GroupAdminFilter
from tgbot.misc.helpers import format_fullname, short_name

logger = logging.getLogger(__name__)

group_admin_router = Router()
group_admin_router.message.filter(
    F.chat.type.in_(("groups", "supergroup")), GroupAdminFilter()
)


def parse_duration(duration_str: str) -> Optional[timedelta]:
    """Парсит строку длительности в timedelta.

    Поддерживает форматы: 1h, 30m, 7d, 1ч, 30м, 7д

    Args:
        duration_str: Строка с длительностью

    Returns:
        Обработанный timedelta
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


@group_admin_router.message(Command("pin"))
async def pin_cmd(message: Message, user: Employee) -> None:
    """Обработчик команды /pin для групп.

    Args:
        message: Сообщение от пользователя
        user: Экземпляр пользователя с моделью Employee
    """
    if not message.reply_to_message:
        await message.reply(
            "🤔 Для закрепления используй команду <code>/pin</code> в ответ на сообщение, которое нужно закрепить"
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
        await message.reply(f"👌 Закрепил <a href='{message_link}'>сообщение</a>")

        # Логируем использование команды
        logger.info(
            f"[/pin] {user.fullname} ({message.from_user.id}) закрепил сообщение в группе {message.chat.id}"
        )

    except Exception as e:
        logger.error(f"Ошибка при закреплении сообщения: {e}")
        await message.reply(
            "🚨 Не смог закрепить сообщение. Возможно, у меня недостаточно прав"
        )


@group_admin_router.message(Command("unpin"))
async def unpin_cmd(message: Message, user: Employee):
    """Обработчик команды /unpin для групп.

    Args:
        message: Сообщение от пользователя
        user: Экземпляр пользователя с моделью Employee
    """
    if not message.reply_to_message:
        await message.reply(
            "🤔 Командой <code>/unpin</code> нужно отвечать на закрепленное сообщение, которое нужно открепить"
        )
        return

    try:
        # Открепляем конкретное сообщение
        await message.bot.unpin_chat_message(
            chat_id=message.chat.id, message_id=message.reply_to_message.message_id
        )

        await message.reply("👌 Закрепленное сообщение откреплено")

        # Логируем использование команды
        logger.info(
            f"[/unpin] {user.fullname} ({message.from_user.id}) открепил сообщение в группе {message.chat.id}"
        )

    except Exception as e:
        logger.error(f"Ошибка при откреплении сообщения: {e}")
        await message.reply(
            "🚨 Не смог открепить сообщение. Возможно, у меня недостаточно прав"
        )


@group_admin_router.message(Command("mute"))
async def mute_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """Обработчик команды /mute для групп.

    Args:
        stp_repo: Репозиторий операций с базой STP
        message: Сообщение от пользователя
        user: Экземпляр пользователя с моделью Employee
    """
    if not message.reply_to_message:
        await message.reply(
            "🤔 Командой <code>/mute</code> нужно отвечать на сообщение пользователя, которого нужно заглушить"
        )
        return

    duration = None
    unmute_at = None

    # Парсим аргументы команды
    command_args = message.text.split()[1:] if message.text else []

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
                "🤔 Используй команду <code>/mute</code> с одним из аргументов: 1h, 30m, 7d, 1ч, 30м, 7д или оставь пустым для постоянного заглушения"
            )
            return

    # Если указана длительность, вычисляем время размута
    if duration:
        unmute_at = datetime.now() + duration

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

        employee = await stp_repo.employee.get_users(user_id=target_user_id)
        if employee:
            display_name = format_fullname(employee, True, True)
        else:
            display_name = target_user_name

        # Формируем сообщение с информацией о заглушении
        if duration:
            if duration.days > 0:
                duration_text = f"{duration.days} дн."
            elif duration.seconds >= 3600:
                duration_text = f"{duration.seconds // 3600} ч."
            else:
                duration_text = f"{duration.seconds // 60} мин."
            mute_message = f"👌 {display_name} заглушен в группе на {duration_text}"
        else:
            mute_message = f"👌 {display_name} заглушен в группе навсегда"

        await message.reply(mute_message)

        # Логируем использование команды
        duration_log = f" на {duration}" if duration else " навсегда"
        logger.info(
            f"[/mute] {user.fullname} ({message.from_user.id}) замутил пользователя {target_user_id} в группе {message.chat.id}{duration_log}"
        )

    except Exception as e:
        logger.error(f"Ошибка при муте пользователя: {e}")
        await message.reply(
            "🚨 Не смог заглушить пользователя. Возможно, у меня недостаточно прав"
        )


@group_admin_router.message(Command("unmute"))
async def unmute_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """Обработчик команды /unmute для групп.

    Args:
        stp_repo: Репозиторий операций с базой STP
        message: Сообщение от пользователя
        user: Экземпляр пользователя с моделью Employee
    """
    if not message.reply_to_message:
        await message.reply(
            "🤔 Командой <code>/unmute</code> нужно отвечать на сообщение пользователя, которого нужно разглушить"
        )
        return

    target_user_id = message.reply_to_message.from_user.id
    target_user_name = (
        message.reply_to_message.from_user.full_name or f"#{target_user_id}"
    )

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

        employee = await stp_repo.employee.get_users(user_id=target_user_id)
        if employee:
            display_name = format_fullname(employee, True, True)
        else:
            display_name = target_user_name

        await message.reply(f"👌 {display_name} разглушен в группе")

        # Логируем использование команды
        logger.info(
            f"[/unmute] {user.fullname} ({message.from_user.id}) разглушил пользователя {target_user_id} в группе {message.chat.id}"
        )

    except Exception as e:
        logger.error(f"Ошибка при размуте пользователя: {e}")
        await message.reply(
            "🚨 Не смог разглушить пользователя. Возможно, у меня недостаточно прав"
        )


@group_admin_router.message(Command("ban"))
async def ban_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """Обработчик команды /ban для групп.

    Args:
        stp_repo: Репозиторий операций с базой STP
        message: Сообщение от пользователя
        user: Экземпляр пользователя с моделью Employee
    """
    if not message.reply_to_message:
        await message.reply(
            "🤔 Командой <code>/ban</code> нужно отвечать на сообщение пользователя, которого нужно заблокировать"
        )
        return

    target_user_id = message.reply_to_message.from_user.id
    target_user_name = (
        message.reply_to_message.from_user.full_name or f"#{target_user_id}"
    )

    try:
        # Блокируем пользователя
        await message.bot.ban_chat_member(
            chat_id=message.chat.id,
            user_id=target_user_id,
        )

        employee = await stp_repo.employee.get_users(user_id=target_user_id)
        if employee:
            display_name = short_name(employee.fullname)
        else:
            display_name = target_user_name

        await message.reply(f"👌 {display_name} заблокирован в группе")

        # Логируем использование команды
        logger.info(
            f"[/ban] {user.fullname} ({message.from_user.id}) забанил пользователя {target_user_id} в группе {message.chat.id}"
        )

    except Exception as e:
        logger.error(f"Ошибка при бане пользователя: {e}")
        await message.reply(
            "🚨 Не смог заблокировать пользователя. Возможно, у меня недостаточно прав"
        )


@group_admin_router.message(Command("unban"), GroupAdminFilter())
async def unban_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """Обработчик команды /unban для групп.

    Args:
        stp_repo: Репозиторий операций с базой STP
        message: Сообщение от пользователя
        user: Экземпляр пользователя с моделью Employee
    """
    if not message.reply_to_message:
        await message.reply(
            "🤔 Командой <code>/unban</code> нужно отвечать на сообщение пользователя, которого нужно разблокировать"
        )
        return

    target_user_id = message.reply_to_message.from_user.id
    target_user_name = (
        message.reply_to_message.from_user.full_name or f"#{target_user_id}"
    )

    try:
        # Разблокируем пользователя
        await message.bot.unban_chat_member(
            chat_id=message.chat.id,
            user_id=target_user_id,
            only_if_banned=True,
        )

        # Получаем информацию о разбаненном пользователе для красивого отображения
        employee = await stp_repo.employee.get_users(user_id=target_user_id)
        if employee:
            display_name = short_name(employee.fullname)
        else:
            display_name = target_user_name

        await message.reply(f"👌 {display_name} разбанен в группе")

        # Логируем использование команды
        logger.info(
            f"[/unban] {user.fullname} ({message.from_user.id}) разбанил пользователя {target_user_id} в группе {message.chat.id}"
        )

    except Exception as e:
        logger.error(f"Ошибка при разбане пользователя: {e}")
        await message.reply(
            "🚨 Не смог разблокировать пользователя. Возможно, у меня недостаточно прав"
        )

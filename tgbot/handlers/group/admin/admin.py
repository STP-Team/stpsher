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

logger = logging.getLogger(__name__)

group_admin_router = Router()
group_admin_router.message.filter(
    F.chat.type.in_(("group", "supergroup")), GroupAdminFilter()
)


def parse_duration(duration_str: str) -> Optional[timedelta]:
    """Парсит строку длительности в timedelta
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


@group_admin_router.message(Command("pin"))
async def pin_cmd(message: Message, user: Employee):
    """/pin для закрепления сообщения"""
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


@group_admin_router.message(Command("unpin"))
async def unpin_cmd(message: Message, user: Employee):
    """/unpin для открепления сообщения"""
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


@group_admin_router.message(Command("mute"))
async def mute_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """/mute для заглушения пользователя"""
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
                    "Неверный формат времени. Используй формат: 1h, 30m, 7d, 1ч, 30м, 7д или оставь пустым для постоянного мута"
                )
                return
    else:
        # Заглушение по user_id из текста команды
        if not command_args:
            await message.reply(
                "Используй команду в ответ на сообщение пользователя, которого хочешь замутить"
            )
            return

        # Первый аргумент - user_id
        try:
            target_user_id = int(command_args[0])
        except ValueError:
            await message.reply(
                "Используй команду /mute <user_id> [время] или ответом на сообщение пользователя"
            )
            return

        # Второй аргумент - длительность (если есть)
        if len(command_args) > 1:
            duration_str = command_args[1]
            duration = parse_duration(duration_str)
            if duration is None:
                await message.reply(
                    "Неверный формат времени. Используй формат: 1h, 30m, 7d, 1ч, 30м, 7д или оставь пустым для постоянного мута"
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
            mute_message = f" {display_name} замьючен в группе на {duration_text}"
        else:
            mute_message = f"{display_name} замьючен в группе навсегда"

        await message.reply(mute_message)

        # Логируем использование команды
        duration_log = f" на {duration}" if duration else " навсегда"
        logger.info(
            f"[/mute] {user.fullname} ({message.from_user.id}) замутил пользователя {target_user_id} в группе {message.chat.id}{duration_log}"
        )

    except Exception as e:
        logger.error(f"Ошибка при муте пользователя: {e}")
        await message.reply("❌ Произошла ошибка при муте пользователя")


@group_admin_router.message(Command("unmute"))
async def unmute_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """/unmute для разглушения пользователя"""
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
                    "Используй команду /unmute <user_id> или ответом на сообщение пользователя"
                )
                return
        else:
            await message.reply(
                "Используй команду в ответ на сообщение пользователя, которого хочешь размутить"
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

        await message.reply(f"{display_name} размьючен в группе")

        # Логируем использование команды
        logger.info(
            f"[/unmute] {user.fullname} ({message.from_user.id}) размутил пользователя {target_user_id} в группе {message.chat.id}"
        )

    except Exception as e:
        logger.error(f"Ошибка при размуте пользователя: {e}")
        await message.reply("❌ Произошла ошибка при размуте пользователя")


@group_admin_router.message(Command("ban"))
async def ban_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """/ban для бана пользователя"""
    target_user_name = "Пользователь"

    # Проверяем способы указания пользователя
    if message.reply_to_message:
        # Бан через ответ на сообщение
        target_user_id = message.reply_to_message.from_user.id
        target_user_name = (
            message.reply_to_message.from_user.full_name or f"#{target_user_id}"
        )
    else:
        # Бан по user_id из текста команды
        command_args = message.text.split()[1:] if message.text else []
        if command_args:
            try:
                target_user_id = int(command_args[0])
            except ValueError:
                await message.reply(
                    "Используй команду /ban <user_id> или ответом на сообщение пользователя"
                )
                return
        else:
            await message.reply(
                "Используй команду в ответ на сообщение пользователя, которого хочешь забанить"
            )
            return

    try:
        # Банируем пользователя в Telegram
        await message.bot.ban_chat_member(
            chat_id=message.chat.id,
            user_id=target_user_id,
        )

        # Получаем информацию о забаненном пользователе для красивого отображения
        employee = await stp_repo.employee.get_user(user_id=target_user_id)
        if employee:
            display_name = short_name(employee.fullname)
        else:
            display_name = target_user_name

        await message.reply(f"{display_name} забанен в группе")

        # Логируем использование команды
        logger.info(
            f"[/ban] {user.fullname} ({message.from_user.id}) забанил пользователя {target_user_id} в группе {message.chat.id}"
        )

    except Exception as e:
        logger.error(f"Ошибка при бане пользователя: {e}")
        await message.reply("❌ Произошла ошибка при бане пользователя")


@group_admin_router.message(Command("unban"), GroupAdminFilter())
async def unban_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """/unban для разбана пользователя"""
    target_user_name = "Пользователь"

    # Проверяем способы указания пользователя
    if message.reply_to_message:
        # Разбан через ответ на сообщение
        target_user_id = message.reply_to_message.from_user.id
        target_user_name = (
            message.reply_to_message.from_user.full_name or f"#{target_user_id}"
        )
    else:
        # Разбан по user_id из текста команды
        command_args = message.text.split()[1:] if message.text else []
        if command_args:
            try:
                target_user_id = int(command_args[0])
            except ValueError:
                await message.reply(
                    "Используй команду /unban <user_id> или ответом на сообщение пользователя"
                )
                return
        else:
            await message.reply(
                "Используй команду в ответ на сообщение пользователя, которого хочешь разбанить"
            )
            return

    try:
        # Разбаниваем пользователя в Telegram
        await message.bot.unban_chat_member(
            chat_id=message.chat.id,
            user_id=target_user_id,
            only_if_banned=True,
        )

        # Получаем информацию о разбаненном пользователе для красивого отображения
        employee = await stp_repo.employee.get_user(user_id=target_user_id)
        if employee:
            display_name = short_name(employee.fullname)
        else:
            display_name = target_user_name

        await message.reply(f"{display_name} разбанен в группе")

        # Логируем использование команды
        logger.info(
            f"[/unban] {user.fullname} ({message.from_user.id}) разбанил пользователя {target_user_id} в группе {message.chat.id}"
        )

    except Exception as e:
        logger.error(f"Ошибка при разбане пользователя: {e}")
        await message.reply("❌ Произошла ошибка при разбане пользователя")

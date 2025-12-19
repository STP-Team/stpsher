"""Сервис рассылок."""

import asyncio
import logging
from typing import Awaitable, Callable, Union

from aiogram import Bot, exceptions
from aiogram.types import InlineKeyboardMarkup


async def send_message(
    bot: Bot,
    user_id: Union[int, str],
    text: str,
    disable_notification: bool = False,
    reply_markup: InlineKeyboardMarkup = None,
) -> bool:
    """Безопасная отправка сообщения.

    Args:
        bot: Экземпляр бота
        user_id: Идентификатор пользователя Telegram
        text: Тест сообщения
        disable_notification: Отключить ли уведомление о сообщении
        reply_markup: Клавиатура к сообщению

    Returns:
        True если сообщение отправлено успешно, иначе False
    """
    try:
        await bot.send_message(
            user_id,
            text,
            disable_notification=disable_notification,
            reply_markup=reply_markup,
        )
    except exceptions.TelegramBadRequest:
        logging.error("Telegram server says - Bad Request: chat not found")
    except exceptions.TelegramForbiddenError:
        logging.error(f"Target [ID:{user_id}]: got TelegramForbiddenError")
    except exceptions.TelegramRetryAfter as e:
        logging.error(
            f"Target [ID:{user_id}]: Flood limit is exceeded. Sleep {e.retry_after} seconds."
        )
        await asyncio.sleep(e.retry_after)
        return await send_message(
            bot, user_id, text, disable_notification, reply_markup
        )  # Рекурсивный вызов
    except exceptions.TelegramAPIError:
        logging.exception(f"Target [ID:{user_id}]: failed")
    else:
        logging.info(f"Target [ID:{user_id}]: success")
        return True
    return False


async def copy_message(
    bot: Bot,
    user_id: Union[int, str],
    from_chat_id: Union[int, str],
    message_id: int,
    disable_notification: bool = False,
) -> bool:
    """Безопасное копирование сообщения.

    Args:
        bot: Экземпляр бота
        user_id: Идентификатор пользователя Telegram
        from_chat_id: Идентификатор чата Telegram, откуда копировать сообщение.
        message_id: Идентификатор сообщения, которое необходимо скопировать.
        disable_notification: Отключить ли уведомление о сообщении

    Returns:
        True если сообщение отправлено успешно, иначе False
    """
    try:
        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=from_chat_id,
            message_id=message_id,
            disable_notification=disable_notification,
        )
    except exceptions.TelegramBadRequest:
        logging.error("Telegram server says - Bad Request: chat not found")
    except exceptions.TelegramForbiddenError:
        logging.error(f"Target [ID:{user_id}]: got TelegramForbiddenError")
    except exceptions.TelegramRetryAfter as e:
        logging.error(
            f"Target [ID:{user_id}]: Flood limit is exceeded. Sleep {e.retry_after} seconds."
        )
        await asyncio.sleep(e.retry_after)
        return await copy_message(
            bot, user_id, from_chat_id, message_id, disable_notification
        )  # Рекурсивный вызов
    except exceptions.TelegramAPIError:
        logging.exception(f"Target [ID:{user_id}]: failed")
    else:
        logging.info(f"Target [ID:{user_id}]: success")
        return True
    return False


async def broadcast(
    bot: Bot,
    users: list[Union[str, int]],
    text: str,
    disable_notification: bool = False,
    reply_markup: InlineKeyboardMarkup = None,
) -> int:
    """Простая рассылка.

    Args:
        bot: Экземпляр бота
        users: Список пользователей с идентификатором Telegram.
        text: Текст сообщения.
        disable_notification: Отключить ли уведомление о сообщении
        reply_markup: Клавиатура к сообщению

    Returns:
        Кол-во успешно отправленных сообщений
    """
    count = 0
    try:
        for user_id in users:
            if await send_message(
                bot, user_id, text, disable_notification, reply_markup
            ):
                count += 1
            await asyncio.sleep(
                0.05
            )  # 20 сообщений в секунду (Лимит: 30 сообщений в секунду)
    finally:
        logging.info(f"{count} messages successful sent.")
        return count


async def broadcast_copy(
    bot: Bot,
    users: list[Union[str, int]],
    from_chat_id: Union[int, str] = None,
    message_id: int = None,
    text: str = None,
    disable_notification: bool = False,
    progress_callback: Callable[[int, int], Awaitable[None]] = None,
) -> tuple[int, int, list[Union[str, int]]]:
    """Рассылка, использующая copy_message или send_message с отслеживанием прогресса.

    Args:
        bot: Экземпляр бота
        users: Список пользователей с идентификатором Telegram.
        from_chat_id: Идентификатор чата Telegram, откуда копировать сообщение.
        message_id: Идентификатор сообщения, которое необходимо скопировать.
        text: Текст сообщения. (опционально если указаны from_chat_id и message_id).
        disable_notification: text: Текст сообщения.
        progress_callback: Callback для отслеживания прогресса рассылки (текущее, общее).

    Returns:
        :return: Кортеж с кол-вом успешных сообщений, ошибок и списком неудачных user_ids
    """
    success_count = 0
    error_count = 0
    failed_user_ids = []
    total = len(users)

    # Validate parameters
    if text is None and (from_chat_id is None or message_id is None):
        raise ValueError(
            "Either 'text' or both 'from_chat_id' and 'message_id' must be provided"
        )

    try:
        for idx, user_id in enumerate(users, 1):
            # Use copy_message if message_id and from_chat_id are provided, otherwise use send_message
            if text is not None:
                success = await send_message(bot, user_id, text, disable_notification)
            else:
                success = await copy_message(
                    bot, user_id, from_chat_id, message_id, disable_notification
                )

            if success:
                success_count += 1
            else:
                error_count += 1
                failed_user_ids.append(user_id)

            # Call progress callback if provided
            if progress_callback:
                await progress_callback(idx, total)

            await asyncio.sleep(
                0.05
            )  # 20 messages per second (Limit: 30 messages per second)
    finally:
        logging.info(
            f"Broadcast completed: {success_count} successful, {error_count} failed."
        )
        return success_count, error_count, failed_user_ids

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
    """Safe messages sender

    :param bot: Bot instance.
    :param user_id: user id. If str - must contain only digits.
    :param text: text of the message.
    :param disable_notification: disable notification or not.
    :param reply_markup: reply markup.
    :return: success.
    """
    try:
        await bot.send_message(
            user_id,
            text,
            disable_notification=disable_notification,
            reply_markup=reply_markup,
            parse_mode="HTML",
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
        )  # Recursive call
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
    """Safe message copier

    :param bot: Bot instance.
    :param user_id: user id to send to. If str - must contain only digits.
    :param from_chat_id: chat id to copy from.
    :param message_id: message id to copy.
    :param disable_notification: disable notification or not.
    :return: success.
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
        )  # Recursive call
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
    """Simple broadcaster.
    :param bot: Bot instance.
    :param users: List of users.
    :param text: Text of the message.
    :param disable_notification: Disable notification or not.
    :param reply_markup: Reply markup.
    :return: Count of messages.
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
            )  # 20 messages per second (Limit: 30 messages per second)
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
) -> tuple[int, int]:
    """Broadcaster using copy_message or send_message with progress tracking.
    :param bot: Bot instance.
    :param users: List of users.
    :param from_chat_id: Chat ID to copy message from (optional if text is provided).
    :param message_id: Message ID to copy (optional if text is provided).
    :param text: Text to send (optional if from_chat_id and message_id are provided).
    :param disable_notification: Disable notification or not.
    :param progress_callback: Optional callback function to track progress (current, total).
    :return: Tuple of (success_count, error_count).
    """
    success_count = 0
    error_count = 0
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
        return success_count, error_count

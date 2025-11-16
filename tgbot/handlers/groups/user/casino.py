"""Обработчики команд казино для групп."""

import asyncio
import logging
import re

from aiogram import F, Router
from aiogram.enums import DiceEmoji
from aiogram.filters import Command
from aiogram.types import Message
from stp_database import Employee, MainRequestsRepo

from tgbot.dialogs.events.common.game.casino import (
    calculate_simple_multiplier,
    calculate_slots_multiplier,
    format_result,
)
from tgbot.filters.group_casino import IsGroupCasinoAllowed

logger = logging.getLogger(__name__)

group_casino_router = Router()
group_casino_router.message.filter(F.chat.type.in_(("group", "supergroup")))


async def send_game_help(message: Message, game_type: str) -> None:
    """Отправить справку по игре.

    Args:
        message: Сообщение от пользователя
        game_type: Тип игры (slots, dice, darts, bowling)
    """
    help_messages = {
        "slots": {
            "title": "🎰 <b>Игра в слоты</b>",
            "usage": "/slots [сумма]",
            "examples": [
                "• /slots 50 - поставить 50 баллов",
                "• /slots 100 - поставить 100 баллов",
            ],
            "rewards": [
                "· Джекпот (777) → 5x",
                "· Три в ряд → 3.5x",
                "· Две семерки → 2.5x",
            ],
        },
        "dice": {
            "title": "🎲 <b>Игра в кости</b>",
            "usage": "/dice [сумма]",
            "examples": [
                "• /dice 50 - поставить 50 баллов",
                "• /dice 100 - поставить 100 баллов",
            ],
            "rewards": [
                "· Выпало 6 → 2x",
                "· Выпало 5 → 1.5x",
                "· Выпало 4 → 0.75x (утешительный приз)",
            ],
        },
        "darts": {
            "title": "🎯 <b>Игра в дартс</b>",
            "usage": "/darts [сумма]",
            "examples": [
                "• /darts 50 - поставить 50 баллов",
                "• /darts 100 - поставить 100 баллов",
            ],
            "rewards": [
                "· Яблочко (6) → 2x",
                "· Близко к центру (5) → 1.5x",
                "· В мишень (4) → 0.75x (утешительный приз)",
            ],
        },
        "bowling": {
            "title": "🎳 <b>Игра в боулинг</b>",
            "usage": "/bowling [сумма]",
            "examples": [
                "• /bowling 50 - поставить 50 баллов",
                "• /bowling 100 - поставить 100 баллов",
            ],
            "rewards": [
                "· Страйк (6) → 2x",
                "· 5 кеглей → 1.5x",
                "· 4 кегли → 0.75x (утешительный приз)",
            ],
        },
    }

    game_info = help_messages[game_type]

    help_text = f"{game_info['title']}\n\n"
    help_text += f"Использование: {game_info['usage']}\n\n"
    help_text += "<b>Примеры:</b>\n"
    help_text += "\n".join(game_info["examples"])
    help_text += "\n\n💎 <b>Таблица наград:</b>\n"
    help_text += "\n".join(game_info["rewards"])
    help_text += "\n\nМинимальная ставка: 10 баллов"

    await message.reply(help_text)


def parse_casino_command(message_text: str) -> int | None:
    """Извлечь ставку из команды казино.

    Args:
        message_text: Текст команды (например, "/slots 50" или "/dice")

    Returns:
        Размер ставки (минимум 10) или None если аргумент не указан
    """
    # Паттерн для извлечения числа из команды
    match = re.search(r"/(?:slots|dice|darts|bowling)\s+(\d+)", message_text)
    if match:
        bet_amount = int(match.group(1))
        return max(10, bet_amount)  # Минимальная ставка 10

    # Проверяем, есть ли команда без аргумента
    if re.search(r"/(?:slots|dice|darts|bowling)$", message_text.strip()):
        return None  # Команда без аргумента

    return 10  # Ставка по умолчанию для других случаев


async def process_casino_game(
    message: Message,
    user: Employee,
    stp_repo: MainRequestsRepo,
    game_type: str,
    dice_emoji: DiceEmoji,
    bet_amount: int,
) -> None:
    """Обработать игру в казино.

    Args:
        message: Сообщение от пользователя
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
        game_type: Тип игры (slots, dice, darts, bowling)
        dice_emoji: Emoji для dice API
        bet_amount: Размер ставки
    """
    try:
        # Проверяем баланс
        user_balance = await stp_repo.transaction.get_user_balance(user.user_id)

        if user_balance < bet_amount:
            await message.reply(
                f"❌ Недостаточно баллов для игры!\n"
                f"✨ Твой баланс: {user_balance} баллов\n"
                f"🎲 Нужно для ставки: {bet_amount} баллов"
            )
            return

        # Отправляем dice и ждем результата
        dice_message = await message.reply_dice(emoji=dice_emoji)
        dice_value = dice_message.dice.value

        # Ждем анимацию (3 секунды)
        await asyncio.sleep(3)

        # Рассчитываем выигрыш
        if game_type == "slots":
            multiplier = calculate_slots_multiplier(dice_value)
        else:
            multiplier = calculate_simple_multiplier(dice_value)

        # Вычисляем чистый выигрыш/проигрыш
        if multiplier > 0:
            gross_win = int(bet_amount * multiplier)
            net_win = gross_win - bet_amount
        else:
            net_win = -bet_amount

        # Обновляем баланс
        if net_win > 0:
            await stp_repo.transaction.add_transaction(
                user_id=user.user_id,
                transaction_type="earn",
                source_type="casino",
                amount=net_win,
                comment=f"Выигрыш в {game_type}: {dice_value} (ставка {bet_amount})",
            )
        elif net_win < 0:
            await stp_repo.transaction.add_transaction(
                user_id=user.user_id,
                transaction_type="spend",
                source_type="casino",
                amount=abs(net_win),
                comment=f"Проигрыш в {game_type}: {dice_value} (ставка {bet_amount})",
            )

        # Получаем новый баланс
        new_balance = await stp_repo.transaction.get_user_balance(user.user_id)

        # Формируем сообщение о результате используя общую функцию
        result_data = format_result(game_type, dice_value, multiplier, net_win)

        # Дополняем информацией о ставке и балансе для групповых команд
        message_parts = [
            f"{result_data['result_icon']} <b>{result_data['result_title']}</b>",
            result_data["result_message"],
            f"\n<b>Ставка:</b> {bet_amount} баллов",
        ]

        # Информация о выигрыше/проигрыше
        if net_win > 0:
            message_parts.append(f"<b>Выиграно:</b> +{net_win} баллов")
        elif net_win < 0:
            message_parts.append(f"<b>Проиграно:</b> {abs(net_win)} баллов")

        message_parts.append(
            f"\n✨ <b>Баланс:</b> {user_balance} → {new_balance} баллов"
        )

        result_message = "\n".join(message_parts)

        await message.reply(result_message)

        # Логируем игру
        user_name = (
            user.fullname
            if user
            else f"@{message.from_user.username}"
            if message.from_user.username
            else message.from_user.full_name
        )
        logger.info(
            f"[Casino/{game_type}] {user_name} ({user.user_id}) играл с ставкой {bet_amount}, "
            f"результат {dice_value}, выигрыш {net_win}"
        )

    except Exception as e:
        logger.error(f"Ошибка в казино {game_type}: {e}")
        await message.reply("🚨 Произошла ошибка при игре в казино. Попробуй позже.")


@group_casino_router.message(Command("slots"), IsGroupCasinoAllowed())
async def slots_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """Обработчик команды /slots для групп.

    Args:
        message: Сообщение от пользователя
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
    """
    bet_amount = parse_casino_command(message.text)
    if bet_amount is None:
        await send_game_help(message, "slots")
        return

    await process_casino_game(
        message, user, stp_repo, "slots", DiceEmoji.SLOT_MACHINE, bet_amount
    )


@group_casino_router.message(Command("dice"), IsGroupCasinoAllowed())
async def dice_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """Обработчик команды /dice для групп.

    Args:
        message: Сообщение от пользователя
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
    """
    bet_amount = parse_casino_command(message.text)
    if bet_amount is None:
        await send_game_help(message, "dice")
        return

    await process_casino_game(
        message, user, stp_repo, "dice", DiceEmoji.DICE, bet_amount
    )


@group_casino_router.message(Command("darts"), IsGroupCasinoAllowed())
async def darts_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """Обработчик команды /darts для групп.

    Args:
        message: Сообщение от пользователя
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
    """
    bet_amount = parse_casino_command(message.text)
    if bet_amount is None:
        await send_game_help(message, "darts")
        return

    await process_casino_game(
        message, user, stp_repo, "darts", DiceEmoji.DART, bet_amount
    )


@group_casino_router.message(Command("bowling"), IsGroupCasinoAllowed())
async def bowling_cmd(message: Message, user: Employee, stp_repo: MainRequestsRepo):
    """Обработчик команды /bowling для групп.

    Args:
        message: Сообщение от пользователя
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
    """
    bet_amount = parse_casino_command(message.text)
    if bet_amount is None:
        await send_game_help(message, "bowling")
        return

    await process_casino_game(
        message, user, stp_repo, "bowling", DiceEmoji.BOWLING, bet_amount
    )

import asyncio
import logging
from functools import lru_cache
from typing import List

from aiogram import F, Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import User
from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.keyboards.user.leveling.casino import (
    CasinoMenu,
    back_to_casino_kb,
    betting_kb,
    casino_main_kb,
    play_again_kb,
)
from tgbot.keyboards.user.main import MainMenu

user_leveling_casino_router = Router()
user_leveling_casino_router.message.filter(
    F.chat.type == "private",
)
user_leveling_casino_router.callback_query.filter(F.message.chat.type == "private")

logger = logging.getLogger(__name__)


@lru_cache(maxsize=64)
def get_score_change(dice_value: int) -> int:
    if dice_value in (1, 22, 43):  # three-of-a-kind (except 777)
        return 7
    elif dice_value in (
        16,
        32,
        48,
        52,
        56,
        60,
        61,
        62,
        63,
    ):  # all combinations with two 7's
        return 5
    elif dice_value == 64:  # jackpot (777)
        return 10
    else:
        return -1


@lru_cache(maxsize=64)
def get_combo_parts(dice_value: int) -> List[str]:
    values = ["bar", "grapes", "lemon", "seven"]

    dice_value -= 1
    result = []
    for _ in range(3):
        result.append(values[dice_value % 4])
        dice_value //= 4
    return result


@lru_cache(maxsize=64)
def get_combo_text(dice_value: int) -> str:
    parts: List[str] = get_combo_parts(dice_value)
    emoji_map = {"bar": "🍫", "grapes": "🍇", "lemon": "🍋", "seven": "7️⃣"}

    emoji_parts = [emoji_map.get(part, part) for part in parts]
    return " ".join(emoji_parts)


def get_slot_result_multiplier(slot_value: int) -> tuple[str, float]:
    score_change = get_score_change(slot_value)
    combo_text = get_combo_text(slot_value)

    if score_change == 10:  # Джекпот (777)
        return f"🎰 {combo_text} - Джекпот! 🎰", 5.0
    elif score_change == 7:  # Три в ряд любых
        return f"🔥 {combo_text} - Три в ряд! 🔥", 3.5
    elif score_change == 5:  # Две семерки
        return f"✨ {combo_text} - Две семерки! ✨", 2.5
    else:  # loss
        return f"{combo_text}", 0.0


def get_dice_result_multiplier(dice_value: int) -> tuple[str, float]:
    # Target: Slots have 20.31% win rate, 58.59% expected return
    # Dice: Only 6 wins to match slots more closely
    if dice_value == 6:  # Единственный выигрыш - 1/6 = 16.67%
        # Expected return: 16.67% × 3.5 = 58.35% (matches slots' 58.59%)
        return f"🎲 {dice_value} - Джекпот! 🎲", 3.5
    else:  # dice_value 1,2,3,4,5 - Проигрыш (5/6 = 83.33%)
        return f"🎲 {dice_value}", 0.0


@user_leveling_casino_router.callback_query(MainMenu.filter(F.menu == "casino"))
async def casino_main_menu(
    callback: CallbackQuery, user: User, stp_repo: MainRequestsRepo
):
    """Главное меню казино"""
    user_balance = await stp_repo.transaction.get_user_balance(user.user_id)

    await callback.message.edit_text(
        f"""🎰 <b>Казино</b>

💰 <b>Баланс:</b> {user_balance} баллов

Выбери игру из списка ниже

🍀 <b>Испытай удачу!</b>""",
        reply_markup=casino_main_kb(),
    )

    logger.info(
        f"[Казино] {callback.from_user.username} ({callback.from_user.id}) открыл главное меню казино"
    )


@user_leveling_casino_router.callback_query(CasinoMenu.filter(F.menu == "main"))
async def casino_main_menu_back(
    callback: CallbackQuery, user: User, stp_repo: MainRequestsRepo
):
    """Возврат в главное меню казино"""
    await casino_main_menu(callback, user, stp_repo)


@user_leveling_casino_router.callback_query(CasinoMenu.filter(F.menu == "slots"))
async def casino_slot_betting(
    callback: CallbackQuery, user: User, stp_repo: MainRequestsRepo
):
    """Выбор ставки для игры в слоты"""
    user_balance = await stp_repo.transaction.get_user_balance(user.user_id)

    if user_balance < 10:
        await callback.message.edit_text(
            """💔 <b>Недостаточно средств!</b>

Минимальная ставка - 10 баллов
Выполняй достижения для заработка баллов!""",
            reply_markup=back_to_casino_kb(),
        )
        return

    await callback.message.edit_text(
        f"""🎰 <b>Казино - Слоты</b>

✨ <b>Баланс:</b> {user_balance} баллов

🎮 <b>Как играть</b>
1. Назначь ставку используя кнопки меню
2. Жми <b>🎰 Крутить 🎰</b>

<blockquote expandable>💎 <b>Таблица наград:</b>
🎰 Джекпот - Три семерки → x5
🔥 Три в ряд → x3.5  
✨ Две семерки → x2.5</blockquote>""",
        reply_markup=betting_kb(user_balance, game_type="slots"),
    )


@user_leveling_casino_router.callback_query(CasinoMenu.filter(F.menu == "dice"))
async def casino_dice_betting(
    callback: CallbackQuery, user: User, stp_repo: MainRequestsRepo
):
    """Выбор ставки для игры в кости"""
    user_balance = await stp_repo.transaction.get_user_balance(user.user_id)

    if user_balance < 10:
        await callback.message.edit_text(
            """💔 <b>Недостаточно средств!</b>

Минимальная ставка - 10 баллов
Выполняй достижения для заработка баллов!""",
            reply_markup=back_to_casino_kb(),
        )
        return

    await callback.message.edit_text(
        f"""🎲 <b>Казино - Кости</b>

✨ <b>Баланс:</b> {user_balance} баллов

🎮 <b>Как играть</b>
1. Назначь ставку используя кнопки меню
2. Жми <b>🎲 Кинуть 🎲</b>

<blockquote expandable>💎 <b>Таблица наград:</b>
🎲 Выпало 6 → x3.5 (Джекпот!)</blockquote>""",
        reply_markup=betting_kb(user_balance, game_type="dice"),
    )


@user_leveling_casino_router.callback_query(CasinoMenu.filter(F.menu == "rate"))
async def casino_rate_adjustment(
    callback: CallbackQuery,
    callback_data: CasinoMenu,
    user: User,
    stp_repo: MainRequestsRepo,
):
    """Регулировка ставки"""
    user_balance = await stp_repo.transaction.get_user_balance(user.user_id)
    new_rate = callback_data.current_rate
    game_type = callback_data.game_type

    if game_type == "dice":
        await callback.message.edit_text(
            f"""🎲 <b>Казино - Кости</b>

✨ <b>Баланс:</b> {user_balance} баллов

🎮 <b>Как играть</b>
1. Назначь ставку используя кнопки меню
2. Жми <b>🎲 Кинуть 🎲</b>

<blockquote expandable>💎 <b>Таблица наград:</b>
🎲 Выпало 6 → x3.5 (Джекпот!)</blockquote>""",
            reply_markup=betting_kb(user_balance, new_rate, game_type),
        )
    else:
        await callback.message.edit_text(
            f"""🎰 <b>Казино - Слоты</b>

✨ <b>Баланс:</b> {user_balance} баллов

🎮 <b>Как играть</b>
1. Назначь ставку используя кнопки меню
2. Жми <b>🎰 Крутить 🎰</b>

<blockquote expandable>💎 <b>Таблица наград:</b>
🎰 Джекпот - Три семерки → x5
🔥 Три в ряд → x3.5  
✨ Две семерки → x2.5</blockquote>""",
            reply_markup=betting_kb(user_balance, new_rate, game_type),
        )


@user_leveling_casino_router.callback_query(CasinoMenu.filter(F.menu == "bet"))
async def casino_game(
    callback: CallbackQuery,
    callback_data: CasinoMenu,
    user: User,
    stp_repo: MainRequestsRepo,
):
    """Игра в казино (слоты или кости)"""
    bet_amount = callback_data.bet_amount
    game_type = callback_data.game_type
    user_balance = await stp_repo.transaction.get_user_balance(user.user_id)

    # Проверим, что у пользователя достаточно средств
    if bet_amount > user_balance:
        await callback.message.edit_text(
            """❌ <b>Недостаточно средств!</b>

Выбери ставку поменьше или заработай больше баллов!""",
            reply_markup=back_to_casino_kb(),
        )
        return

    # Информируем о начале игры
    if game_type == "dice":
        await callback.message.edit_text(
            f"""🎲 <b>Кидаем кости...</b>

💰 <b>Ставка:</b> {bet_amount} баллов
⏰ <b>Ждем результат...</b>

<blockquote expandable>💎 <b>Таблица наград:</b>
🎲 Выпало 6 → x3.5 (Джекпот!)</blockquote>"""
        )

        # Отправляем настоящие кости с анимацией!
        dice_result = await callback.message.answer_dice(emoji="🎲")
        dice_value = dice_result.dice.value

        # Ждем анимацию кости (около 2 секунд)
        await asyncio.sleep(2)

        # Определяем результат
        result_text, multiplier = get_dice_result_multiplier(dice_value)
        game_name = "костях"
    else:
        await callback.message.edit_text(
            f"""🎰 <b>Крутим барабан...</b>

💰 <b>Ставка:</b> {bet_amount} баллов
⏰ <b>Ждем результат...</b>

<blockquote expandable>💎 <b>Таблица наград:</b>
🎰 Джекпот - Три семерки → x5
🔥 Три в ряд → x3.5  
✨ Две семерки → x2.5</blockquote>"""
        )

        # Отправляем настоящую слот-машину с анимацией!
        slot_result = await callback.message.answer_dice(emoji="🎰")
        slot_value = slot_result.dice.value

        # Ждем анимацию слота (около 2 секунд)
        await asyncio.sleep(2)

        # Определяем результат
        result_text, multiplier = get_slot_result_multiplier(slot_value)
        game_name = "слотах"

    if multiplier > 0:
        # Выигрыш
        winnings = int(bet_amount * multiplier)

        # Записываем транзакцию выигрыша
        await stp_repo.transaction.add_transaction(
            user_id=user.user_id,
            type="earn",
            source_type="casino",
            amount=winnings,
            comment=f"Выигрыш в {game_name}: {result_text} (x{multiplier})",
        )

        new_balance = await stp_repo.transaction.get_user_balance(user.user_id)
        final_result = f"""🎉 <b>Победа</b> 🎉

{result_text}

🔥 Выигрыш: {bet_amount} x{multiplier} = {winnings} баллов!
✨ Баланс: {new_balance - bet_amount} → {new_balance} баллов"""

        logger.info(
            f"[Казино] {callback.from_user.username} выиграл {winnings} баллов в {game_name} ({result_text})"
        )

    else:
        # Проигрыш
        # Списываем ставку
        await stp_repo.transaction.add_transaction(
            user_id=user.user_id,
            type="spend",
            source_type="casino",
            amount=bet_amount,
            comment=f"Проигрыш в {game_name}: {result_text}",
        )

        new_balance = await stp_repo.transaction.get_user_balance(user.user_id)
        final_result = f"""💔 <b>Проигрыш</b>

{result_text}

💸 Потрачено: -{bet_amount} баллов
✨ Баланс: {new_balance + bet_amount} → {new_balance} баллов

<i>Попробуй еще раз - удача рядом!</i>"""

        logger.info(
            f"[Казино] {callback.from_user.username} проиграл {bet_amount} баллов в {game_name} ({result_text})"
        )

    # Показываем финальный результат
    await callback.message.answer(
        final_result,
        reply_markup=play_again_kb(bet_amount, game_type),
    )

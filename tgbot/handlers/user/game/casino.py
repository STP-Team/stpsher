import asyncio
import logging
from functools import lru_cache
from typing import List

from aiogram import F, Router
from aiogram.types import CallbackQuery
from stp_database import Employee
from stp_database.repo.STP.requests import MainRequestsRepo

from tgbot.filters.casino import IsCasinoAllowed
from tgbot.keyboards.user.game.casino import (
    CasinoMenu,
    back_to_casino_kb,
    betting_kb,
    casino_main_kb,
    play_again_kb,
)
from tgbot.keyboards.user.game.main import GameMenu

user_game_casino_router = Router()
user_game_casino_router.message.filter(
    F.chat.type == "private",
)
user_game_casino_router.callback_query.filter(F.message.chat.type == "private")

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
    # Побеждает только 5 и 6. Шанс победы - 33%
    if dice_value == 6:
        return f"🎲 {dice_value} - Джекпот! 🎲", 2.0
    if dice_value == 5:
        return f"🎲 {dice_value} - Множитель 1.5x! 🎲", 1.5
    if dice_value == 4:
        return f"🎲 {dice_value} - Утешительный приз 🎲", 0.75
    else:
        return f"🎲 {dice_value}", 0.0


def get_darts_result_multiplier(dice_value: int) -> tuple[str, float]:
    # Побеждает только 5 и 6. Шанс победы - 33%
    if dice_value == 6:
        return f"🎯 {dice_value} - Джекпот! 🎯", 2.0
    if dice_value == 5:
        return f"🎯 {dice_value} - Почти попали! 🎯", 1.5
    if dice_value == 4:
        return f"🎯 {dice_value} - Утешительный приз 🎯", 0.75
    else:
        return f"🎯 {dice_value}", 0.0


def get_bowling_result_multiplier(dice_value: int) -> tuple[str, float]:
    # Побеждает только 5 и 6. Шанс победы - 33%
    if dice_value == 6:
        return f"🎳 {dice_value} - Все кегли сбиты! 🎳", 2.0
    elif dice_value == 5:
        return f"🎳 {dice_value} - Сбито 5 кеглей! 🎳", 1.5
    elif dice_value == 4:
        return f"🎳 {dice_value} - Утешительный приз! 🎳", 0.75
    else:
        return f"🎳 {dice_value}", 0.0


@user_game_casino_router.callback_query(
    GameMenu.filter(F.menu == "casino"), IsCasinoAllowed()
)
async def casino_main_menu(
    callback: CallbackQuery, user: Employee, stp_repo: MainRequestsRepo
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


@user_game_casino_router.callback_query(
    CasinoMenu.filter(F.menu == "main"), IsCasinoAllowed()
)
async def casino_main_menu_back(
    callback: CallbackQuery, user: Employee, stp_repo: MainRequestsRepo
):
    """Возврат в главное меню казино"""
    await casino_main_menu(callback, user, stp_repo)


@user_game_casino_router.callback_query(
    CasinoMenu.filter(F.menu == "slots"), IsCasinoAllowed()
)
async def casino_slot_betting(
    callback: CallbackQuery, user: Employee, stp_repo: MainRequestsRepo
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
🎰 Джекпот - Три семерки → x5.0
🔥 Три в ряд → x3.5
✨ Две семерки → x2.5</blockquote>""",
        reply_markup=betting_kb(user_balance, game_type="slots"),
    )


@user_game_casino_router.callback_query(
    CasinoMenu.filter(F.menu == "dice"), IsCasinoAllowed()
)
async def casino_dice_betting(
    callback: CallbackQuery, user: Employee, stp_repo: MainRequestsRepo
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
· Выпало 6 → 2x
· Выпало 5 → 1.5x
· Выпало 4 → 0.75x (утешительный приз)

Остальные комбинации проигрышные</blockquote>""",
        reply_markup=betting_kb(user_balance, game_type="dice"),
    )


@user_game_casino_router.callback_query(
    CasinoMenu.filter(F.menu == "darts"), IsCasinoAllowed()
)
async def casino_darts_betting(
    callback: CallbackQuery, user: Employee, stp_repo: MainRequestsRepo
):
    """Выбор ставки для игры в дартс"""
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
        f"""🎯 <b>Казино - Дартс</b>

✨ <b>Баланс:</b> {user_balance} баллов

🎮 <b>Как играть</b>
1. Назначь ставку используя кнопки меню
2. Жми <b>🎯 Бросить 🎯</b>

<blockquote expandable>💎 <b>Таблица наград:</b>
· В яблочко → 2x
· 1 кольцо от центра → 1.5x
· 2 кольцо от центра → 0.75x (утешительный приз)

Остальные комбинации проигрышные</blockquote>""",
        reply_markup=betting_kb(user_balance, game_type="darts"),
    )


@user_game_casino_router.callback_query(
    CasinoMenu.filter(F.menu == "bowling"), IsCasinoAllowed()
)
async def casino_bowling_betting(
    callback: CallbackQuery, user: Employee, stp_repo: MainRequestsRepo
):
    """Выбор ставки для игры в боулинг"""
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
        f"""🎳 <b>Казино - Боулинг</b>

✨ <b>Баланс:</b> {user_balance} баллов

🎮 <b>Как играть</b>
1. Назначь ставку используя кнопки меню
2. Жми <b>🎳 Катить 🎳</b>

<blockquote expandable>💎 <b>Таблица наград:</b>
· Страйк → 2x
· 5 кеглей → 1.5x
· 4 кегли → 0.75x (утешительный приз)

Остальные комбинации проигрышные</blockquote>""",
        reply_markup=betting_kb(user_balance, game_type="bowling"),
    )


@user_game_casino_router.callback_query(
    CasinoMenu.filter(F.menu == "rate"), IsCasinoAllowed()
)
async def casino_rate_adjustment(
    callback: CallbackQuery,
    callback_data: CasinoMenu,
    user: Employee,
    stp_repo: MainRequestsRepo,
):
    """Регулировка ставки"""
    user_balance = await stp_repo.transaction.get_user_balance(user.user_id)
    new_rate = callback_data.current_rate
    game_type = callback_data.game_type

    game_info = {
        "dice": {
            "title": "🎲 <b>Казино - Кости</b>",
            "action": "🎲 Кинуть 🎲",
            "rewards": """· Выпало 6 → 2x
· Выпало 5 → 1.5x
· Выпало 4 → 0.75x (утешительный приз)""",
        },
        "darts": {
            "title": "🎯 <b>Казино - Дартс</b>",
            "action": "🎯 Бросить 🎯",
            "rewards": """· В яблочко → 2x
· 1 кольцо от центра → 1.5x
· 2 кольцо от центра → 0.75x (утешительный приз)""",
        },
        "bowling": {
            "title": "🎳 <b>Казино - Боулинг</b>",
            "action": "🎳 Катить 🎳",
            "rewards": """· Страйк → 2x
· 5 кеглей → 1.5x
· 4 кегли → 0.75x (утешительный приз)""",
        },
        "slots": {
            "title": "🎰 <b>Казино - Слоты</b>",
            "action": "🎰 Крутить 🎰",
            "rewards": """🎰 Джекпот - Три семерки → x5.0
🔥 Три в ряд → x3.5
✨ Две семерки → x2.5""",
        },
    }

    info = game_info.get(game_type, game_info["slots"])
    await callback.message.edit_text(
        f"""{info["title"]}

✨ <b>Баланс:</b> {user_balance} баллов

🎮 <b>Как играть</b>
1. Назначь ставку используя кнопки меню
2. Жми <b>{info["action"]}</b>

<blockquote expandable>💎 <b>Таблица наград:</b>
{info["rewards"]}</blockquote>""",
        reply_markup=betting_kb(user_balance, new_rate, game_type),
    )


@user_game_casino_router.callback_query(
    CasinoMenu.filter(F.menu == "bet"), IsCasinoAllowed()
)
async def casino_game(
    callback: CallbackQuery,
    callback_data: CasinoMenu,
    user: Employee,
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

    # Настройки для разных игр
    game_config = {
        "dice": {
            "loading_text": "🎲 <b>Кидаем кости...</b>",
            "emoji": "🎲",
            "multiplier_func": get_dice_result_multiplier,
            "game_name": "костях",
            "rewards": """· Выпало 6 → 2x
· Выпало 5 → 1.5x
· Выпало 4 → 0.75x (утешительный приз)""",
        },
        "darts": {
            "loading_text": "🎯 <b>Бросаем дартс...</b>",
            "emoji": "🎯",
            "multiplier_func": get_darts_result_multiplier,
            "game_name": "дартсе",
            "rewards": """· В яблочко → 2x
· 1 кольцо от центра → 1.5x
· 2 кольцо от центра → 0.75x (утешительный приз)""",
        },
        "bowling": {
            "loading_text": "🎳 <b>Катим шар...</b>",
            "emoji": "🎳",
            "multiplier_func": get_bowling_result_multiplier,
            "game_name": "боулинге",
            "rewards": """· Страйк → 2x
· 5 кеглей → 1.5x
· 4 кегли → 0.75x (утешительный приз)""",
        },
        "slots": {
            "loading_text": "🎰 <b>Крутим барабан...</b>",
            "emoji": "🎰",
            "multiplier_func": get_slot_result_multiplier,
            "game_name": "слотах",
            "rewards": """🎰 Джекпот - Три семерки → x5.0
🔥 Три в ряд → x3.5
✨ Две семерки → x2.5""",
        },
    }

    config = game_config.get(game_type, game_config["slots"])

    # Информируем о начале игры
    await callback.message.edit_text(
        f"""{config["loading_text"]}

💰 <b>Ставка:</b> {bet_amount} баллов
⏰ <b>Ждем результат...</b>

<blockquote expandable>💎 <b>Таблица наград:</b>
{config["rewards"]}</blockquote>"""
    )

    # Отправляем анимированную игру
    game_result = await callback.message.answer_dice(emoji=config["emoji"])
    game_value = game_result.dice.value

    # Ждем анимацию (около 3 секунд для кубика и 2 секунды для казино)
    if game_type == "dice":
        await asyncio.sleep(3)
    else:
        await asyncio.sleep(2)

    # Определяем результат
    result_text, multiplier = config["multiplier_func"](game_value)
    game_name = config["game_name"]

    if multiplier > 0:
        # Выигрыш
        winnings = int(bet_amount * multiplier)
        net_result = winnings - bet_amount

        if net_result > 0:
            # Чистый выигрыш - записываем earn транзакцию
            transaction, new_balance = await stp_repo.transaction.add_transaction(
                user_id=user.user_id,
                transaction_type="earn",
                source_type="casino",
                amount=net_result,
                comment=f"Выигрыш в {game_name}: {result_text} (x{multiplier})",
            )
        else:
            # Утешительный приз меньше ставки - записываем spend транзакцию
            transaction, new_balance = await stp_repo.transaction.add_transaction(
                user_id=user.user_id,
                transaction_type="spend",
                source_type="casino",
                amount=abs(net_result),
                comment=f"Утешительный приз в {game_name}: {result_text} (x{multiplier})",
            )

        final_result = f"""🎉 <b>Победа</b> 🎉

{result_text}

🔥 Выигрыш: {bet_amount} x{multiplier} = {winnings} баллов!
✨ Баланс: {user_balance - bet_amount} → {new_balance} баллов"""

        logger.info(
            f"[Казино] {callback.from_user.username} выиграл {winnings} баллов в {game_name} ({result_text})"
        )

    else:
        # Проигрыш
        # Списываем ставку
        transaction, new_balance = await stp_repo.transaction.add_transaction(
            user_id=user.user_id,
            transaction_type="spend",
            source_type="casino",
            amount=bet_amount,
            comment=f"Проигрыш в {game_name}: {result_text}",
        )

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

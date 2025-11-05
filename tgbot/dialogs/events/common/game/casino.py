"""Обработчики событий казино."""

import asyncio
from typing import Dict

from aiogram.enums import DiceEmoji
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button
from stp_database import Employee, MainRequestsRepo

from tgbot.dialogs.states.common.game import Game


async def check_casino_access(
    event: CallbackQuery,
    dialog_manager: DialogManager,
) -> bool:
    """Проверить доступ пользователя к казино.

    Args:
        event: Callback query от пользователя
        dialog_manager: Менеджер диалога

    Returns:
        True если доступ разрешен, False если запрещен
    """
    user: Employee = dialog_manager.middleware_data["user"]

    if user is None or not user.is_casino_allowed:
        await event.answer(
            "Казино недоступно. Обратитесь к руководителю если считаешь это ошибкой",
            show_alert=True,
        )
        return False

    return True


async def change_rate(
    _event: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик изменения ставки.

    Args:
        _event: Callback query от пользователя
        widget: Button виджет
        dialog_manager: Менеджер диалога
    """
    # Получаем значение изменения из button.widget_id
    # Формат: rate_minus_50 или rate_plus_50
    widget_id = widget.widget_id
    if "minus" in widget_id:
        delta = -int(widget_id.split("_")[-1])
    else:  # "plus" in widget_id
        delta = int(widget_id.split("_")[-1])

    # Получаем текущую ставку
    current_rate = dialog_manager.dialog_data.get("casino_rate", 10)

    # Вычисляем новую ставку
    new_rate = max(10, current_rate + delta)

    # Сохраняем новую ставку
    dialog_manager.dialog_data["casino_rate"] = new_rate


def calculate_slots_multiplier(value: int) -> float:
    """Рассчитать множитель для слотов.

    Args:
        value: Значение слота (1-64)

    Returns:
        Множитель выигрыша
    """
    # Логика слотов из старой версии:
    # Джекпот (777) - value 64: x5.0
    # Три одинаковых - values 1,22,43: x3.5
    # Две семерки - values 16,32,48: x2.5
    if value == 64:  # Джекпот 777
        return 5.0
    elif value in [1, 22, 43]:  # Три одинаковых символа
        return 3.5
    elif value in [16, 32, 48]:  # Две семерки
        return 2.5
    return 0.0


def calculate_simple_multiplier(value: int) -> float:
    """Рассчитать множитель для простых игр (dice, darts, bowling).

    Args:
        value: Результат броска (1-6)

    Returns:
        Множитель выигрыша
    """
    if value == 6:
        return 2.0
    elif value == 5:
        return 1.5
    elif value == 4:
        return 0.75
    return 0.0


async def play_casino_game(
    event: CallbackQuery,
    dialog_manager: DialogManager,
    stp_repo: MainRequestsRepo,
    user: Employee,
    game_type: str,
    dice_emoji: DiceEmoji,
) -> None:
    """Общая логика для запуска казино-игры.

    Args:
        user: Экземпляр пользователя с моделью Employee.
        stp_repo: Репозиторий операций с базой STP
        event: Callback query от пользователя
        dialog_manager: Менеджер диалога
        game_type: Тип игры (slots, dice, darts, bowling)
        dice_emoji: Emoji для dice API
    """
    # Получаем текущую ставку и баланс
    current_rate = dialog_manager.dialog_data.get("casino_rate", 10)
    user_balance = await stp_repo.transaction.get_user_balance(user.user_id)

    # Проверяем баланс
    if user_balance < current_rate:
        await event.answer("Недостаточно баллов для игры!", show_alert=True)
        return

    # Сохраняем тип игры и старый баланс
    dialog_manager.dialog_data["casino_game_type"] = game_type
    dialog_manager.dialog_data["old_balance"] = user_balance

    # Убираем кнопки с текущего сообщения перед отправкой dice
    await event.message.edit_reply_markup(reply_markup=None)

    # Отправляем dice и ждем результата
    dice_message = await event.message.answer_dice(emoji=dice_emoji)
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
        gross_win = int(current_rate * multiplier)
        net_win = gross_win - current_rate
    else:
        net_win = -current_rate

    # Обновляем баланс
    if net_win > 0:
        await stp_repo.transaction.add_transaction(
            user_id=user.user_id,
            transaction_type="earn",
            source_type="casino",
            amount=net_win,
            comment=f"Выигрыш в {game_type}: {dice_value} (ставка {current_rate})",
        )
    elif net_win < 0:
        await stp_repo.transaction.add_transaction(
            user_id=user.user_id,
            transaction_type="spend",
            source_type="casino",
            amount=abs(net_win),
            comment=f"Проигрыш в {game_type}: {dice_value} (ставка {current_rate})",
        )

    # Формируем результат
    result_data = format_result(game_type, dice_value, multiplier, net_win)
    dialog_manager.dialog_data.update(result_data)
    dialog_manager.dialog_data["win_amount"] = net_win

    # Переходим к окну результата с новым сообщением
    dialog_manager.show_mode = ShowMode.SEND
    await dialog_manager.switch_to(Game.casino_result)


def format_result(game_type: str, value: int, multiplier: float, net_win: int) -> Dict:
    """Форматировать результат игры.

    Args:
        game_type: Тип игры
        value: Значение результата
        multiplier: Множитель выигрыша
        net_win: Чистый выигрыш

    Returns:
        Словарь с данными результата
    """
    if net_win > 0:
        result_icon = "🎉"
        result_title = "Победа!"
    elif net_win == 0:
        result_icon = "😐"
        result_title = "Ничья"
    else:
        result_icon = "😔"
        result_title = "Проигрыш"

    # Формируем сообщение в зависимости от типа игры
    if game_type == "slots":
        if value == 64:
            result_message = "🎰 <b>ДЖЕКПОТ!</b> Три семерки!"
        elif value in [1, 22, 43]:
            result_message = "🔥 <b>Три в ряд!</b> Отличный результат!"
        elif value in [16, 32, 48]:
            result_message = "✨ <b>Две семерки!</b> Неплохо!"
        else:
            result_message = "Не повезло в этот раз..."
    elif game_type == "dice":
        if value == 6:
            result_message = f"🎯 Выпало <b>{value}</b>! Отлично!"
        elif value == 5:
            result_message = f"✨ Выпало <b>{value}</b>! Хорошо!"
        elif value == 4:
            result_message = f"💫 Выпало <b>{value}</b>! Неплохо!"
        else:
            result_message = f"Выпало <b>{value}</b>. Не повезло..."
    elif game_type == "darts":
        if value == 6:
            result_message = "🎯 <b>Яблочко!</b> Идеальный бросок!"
        elif value == 5:
            result_message = "✨ <b>Близко к центру!</b> Хороший бросок!"
        elif value == 4:
            result_message = "💫 <b>В мишень!</b> Неплохо!"
        else:
            result_message = f"Попадание на <b>{value}</b>. Промах..."
    else:  # bowling
        if value == 6:
            result_message = "🎳 <b>СТРАЙК!</b> Все кегли сбиты!"
        elif value == 5:
            result_message = "✨ <b>Почти страйк!</b> 5 кеглей!"
        elif value == 4:
            result_message = "💫 <b>Хороший бросок!</b> 4 кегли!"
        else:
            result_message = f"Сбито <b>{value}</b> кеглей. Слабовато..."

    if multiplier > 0:
        result_message += f"\n🎁 <b>Множитель:</b> x{multiplier}"

    return {
        "result_icon": result_icon,
        "result_title": result_title,
        "result_message": result_message,
    }


async def start_slots(
    event: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик запуска игры в слоты.

    Args:
        event: Callback query от пользователя
        widget: Button виджет
        dialog_manager: Менеджер диалога
    """
    if not await check_casino_access(event, dialog_manager):
        return

    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user: Employee = dialog_manager.middleware_data["user"]

    await play_casino_game(
        event, dialog_manager, stp_repo, user, "slots", DiceEmoji.SLOT_MACHINE
    )


async def start_dice(
    event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик запуска игры в кости.

    Args:
        event: Callback query от пользователя
        _widget: Button виджет
        dialog_manager: Менеджер диалога
    """
    if not await check_casino_access(event, dialog_manager):
        return

    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user: Employee = dialog_manager.middleware_data["user"]

    await play_casino_game(
        event, dialog_manager, stp_repo, user, "dice", DiceEmoji.DICE
    )


async def start_darts(
    event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик запуска игры в дартс.

    Args:
        event: Callback query от пользователя
        _widget: Button виджет
        dialog_manager: Менеджер диалога
    """
    if not await check_casino_access(event, dialog_manager):
        return

    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user: Employee = dialog_manager.middleware_data["user"]

    await play_casino_game(
        event, dialog_manager, stp_repo, user, "darts", DiceEmoji.DART
    )


async def start_bowling(
    event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик запуска игры в боулинг.

    Args:
        event: Callback query от пользователя
        _widget: Button виджет
        dialog_manager: Менеджер диалога
    """
    if not await check_casino_access(event, dialog_manager):
        return

    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user: Employee = dialog_manager.middleware_data["user"]

    await play_casino_game(
        event, dialog_manager, stp_repo, user, "bowling", DiceEmoji.BOWLING
    )


async def play_again(
    event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик повторной игры - сразу запускает ту же игру.

    Args:
        event: Callback query от пользователя
        _widget: Button виджет
        dialog_manager: Менеджер диалога
    """
    if not await check_casino_access(event, dialog_manager):
        return

    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user: Employee = dialog_manager.middleware_data["user"]

    # Получаем тип игры из dialog_data
    game_type = dialog_manager.dialog_data.get("casino_game_type", "slots")

    # Маппинг типов игр на emoji
    game_emojis = {
        "slots": DiceEmoji.SLOT_MACHINE,
        "dice": DiceEmoji.DICE,
        "darts": DiceEmoji.DART,
        "bowling": DiceEmoji.BOWLING,
    }

    # Запускаем игру снова с теми же параметрами
    await play_casino_game(
        event,
        dialog_manager,
        stp_repo,
        user,
        game_type,
        game_emojis.get(game_type, DiceEmoji.SLOT_MACHINE),
    )

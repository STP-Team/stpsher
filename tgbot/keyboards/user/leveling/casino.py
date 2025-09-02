from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.main import MainMenu


class CasinoMenu(CallbackData, prefix="casino"):
    menu: str
    bet_amount: int = 0
    current_rate: int = 10


def casino_main_kb() -> InlineKeyboardMarkup:
    """Главная клавиатура казино"""
    buttons = [
        [
            InlineKeyboardButton(
                text="🎰 Играть в слоты",
                callback_data=CasinoMenu(menu="slots").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def betting_kb(user_balance: int, current_rate: int = None) -> InlineKeyboardMarkup:
    """Стильная клавиатура выбора ставки"""
    # Если current_rate не указан, устанавливаем 1/10 от баланса, но не менее 10
    if current_rate is None:
        current_rate = max(10, user_balance // 10)

    buttons = []

    # Первый ряд: текущая ставка крупно
    buttons.append(
        [
            InlineKeyboardButton(
                text=f"💎 СТАВКА: {current_rate} 💎",
                callback_data="noop",
            )
        ]
    )

    # Второй ряд: главная кнопка Крутить
    buttons.append(
        [
            InlineKeyboardButton(
                text="🎰 Крутить 🎰",
                callback_data=CasinoMenu(menu="bet", bet_amount=current_rate).pack(),
            )
        ]
    )

    # Третий ряд: быстрая регулировка
    adjust_row = []

    # -50
    if current_rate - 50 >= 10:
        adjust_row.append(
            InlineKeyboardButton(
                text="⬇️ -50",
                callback_data=CasinoMenu(
                    menu="rate", current_rate=current_rate - 50
                ).pack(),
            )
        )

    # -10
    if current_rate - 10 >= 10:
        adjust_row.append(
            InlineKeyboardButton(
                text="➖ -10",
                callback_data=CasinoMenu(
                    menu="rate", current_rate=current_rate - 10
                ).pack(),
            )
        )

    # +10
    if current_rate + 10 <= user_balance:
        adjust_row.append(
            InlineKeyboardButton(
                text="➕ +10",
                callback_data=CasinoMenu(
                    menu="rate", current_rate=current_rate + 10
                ).pack(),
            )
        )

    # +50
    if current_rate + 50 <= user_balance:
        adjust_row.append(
            InlineKeyboardButton(
                text="⬆️ +50",
                callback_data=CasinoMenu(
                    menu="rate", current_rate=current_rate + 50
                ).pack(),
            )
        )

    if adjust_row:
        buttons.append(adjust_row)

    # Четвертый ряд: большие регулировки
    big_adjust_row = []

    # -500
    if current_rate - 500 >= 10:
        big_adjust_row.append(
            InlineKeyboardButton(
                text="⬇️ -500",
                callback_data=CasinoMenu(
                    menu="rate", current_rate=current_rate - 500
                ).pack(),
            )
        )

    # -100
    if current_rate - 100 >= 10:
        big_adjust_row.append(
            InlineKeyboardButton(
                text="⬇️ -100",
                callback_data=CasinoMenu(
                    menu="rate", current_rate=current_rate - 100
                ).pack(),
            )
        )

    # +100
    if current_rate + 100 <= user_balance:
        big_adjust_row.append(
            InlineKeyboardButton(
                text="⬆️ +100",
                callback_data=CasinoMenu(
                    menu="rate", current_rate=current_rate + 100
                ).pack(),
            )
        )

    # +500
    if current_rate + 500 <= user_balance:
        big_adjust_row.append(
            InlineKeyboardButton(
                text="⬆️ +500",
                callback_data=CasinoMenu(
                    menu="rate", current_rate=current_rate + 500
                ).pack(),
            )
        )

    if big_adjust_row:
        buttons.append(big_adjust_row)

    # Шестой ряд: особые ставки в одном ряду
    special_row = []

    # Половина баланса
    half_balance = user_balance // 2
    if half_balance >= 10 and half_balance != current_rate:
        special_row.append(
            InlineKeyboardButton(
                text=f"⚖️ Половина ({half_balance})",
                callback_data=CasinoMenu(menu="rate", current_rate=half_balance).pack(),
            )
        )

    # All-in в том же ряду
    if user_balance > current_rate and user_balance >= 10:
        special_row.append(
            InlineKeyboardButton(
                text=f"🔥 All-in ({user_balance})",
                callback_data=CasinoMenu(menu="rate", current_rate=user_balance).pack(),
            )
        )

    if special_row:
        buttons.append(special_row)

    # Последний ряд: навигация
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=CasinoMenu(menu="main").pack()
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def play_again_kb(last_bet: int = 0) -> InlineKeyboardMarkup:
    """Удобная клавиатура после игры"""
    buttons = [
        [
            InlineKeyboardButton(
                text="⚖️ Изменить ставку",
                callback_data=CasinoMenu(menu="slots").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🎰 Казино",
                callback_data=MainMenu(menu="casino").pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    # Если была предыдущая ставка, добавляем быструю кнопку повтора
    if last_bet > 0:
        buttons.insert(
            0,
            [
                InlineKeyboardButton(
                    text=f"⚡ Повтор {last_bet}",
                    callback_data=CasinoMenu(menu="bet", bet_amount=last_bet).pack(),
                ),
            ],
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_casino_kb() -> InlineKeyboardMarkup:
    """Клавиатура для возврата в казино"""
    buttons = [
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=CasinoMenu(menu="main").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

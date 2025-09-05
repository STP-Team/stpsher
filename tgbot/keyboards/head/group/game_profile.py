from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.user.main import MainMenu
from tgbot.keyboards.head.group.members import HeadMemberDetailMenu


class HeadMemberGameProfileMenu(CallbackData, prefix="head_member_game_profile"):
    member_id: int
    page: int = 1


class HeadMemberGameHistoryMenu(CallbackData, prefix="head_member_game_history"):
    member_id: int
    history_page: int = 1
    page: int = 1


class HeadMemberTransactionDetailMenu(
    CallbackData, prefix="head_member_transaction_detail"
):
    member_id: int
    transaction_id: int
    history_page: int = 1
    page: int = 1


def head_member_game_profile_kb(member_id: int, page: int = 1) -> InlineKeyboardMarkup:
    """
    Клавиатура для игрового профиля участника группы
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="📜 История баланса",
                callback_data=HeadMemberGameHistoryMenu(
                    member_id=member_id, history_page=1, page=page
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=HeadMemberDetailMenu(
                    member_id=member_id, page=page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def head_member_game_history_kb(
    member_id: int,
    transactions,
    current_page: int = 1,
    page: int = 1,
    transactions_per_page: int = 8,
) -> InlineKeyboardMarkup:
    """
    Клавиатура истории транзакций участника группы с пагинацией
    """
    buttons = []

    if not transactions:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="↩️ Назад",
                    callback_data=HeadMemberGameProfileMenu(
                        member_id=member_id, page=page
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
                ),
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    # Рассчитываем пагинацию
    total_transactions = len(transactions)
    total_pages = (
        total_transactions + transactions_per_page - 1
    ) // transactions_per_page

    # Рассчитываем диапазон транзакций для текущей страницы
    start_idx = (current_page - 1) * transactions_per_page
    end_idx = start_idx + transactions_per_page
    page_transactions = transactions[start_idx:end_idx]

    # Создаем кнопки для транзакций (2 в ряд)
    for i in range(0, len(page_transactions), 2):
        row = []

        # Первая транзакция в ряду
        transaction = page_transactions[i]
        type_emoji = "➕" if transaction.type == "earn" else "➖"
        date_str = transaction.created_at.strftime("%d.%m.%y")
        amount_str = f"{transaction.amount}"

        # Определяем источник кратко
        source_icons = {
            "achievement": "🏆",
            "product": "🛒",
            "manual": "✍️",
            "casino": "🎰",
        }
        source_icon = source_icons.get(transaction.source_type, "❓")

        button_text = f"{type_emoji} {amount_str} {source_icon} ({date_str})"

        row.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=HeadMemberTransactionDetailMenu(
                    member_id=member_id,
                    transaction_id=transaction.id,
                    history_page=current_page,
                    page=page,
                ).pack(),
            )
        )

        # Вторая транзакция в ряду (если есть)
        if i + 1 < len(page_transactions):
            transaction = page_transactions[i + 1]
            type_emoji = "➕" if transaction.type == "earn" else "➖"
            date_str = transaction.created_at.strftime("%d.%m.%y")
            amount_str = f"{transaction.amount}"

            source_icon = source_icons.get(transaction.source_type, "❓")
            button_text = f"{type_emoji} {amount_str} {source_icon} ({date_str})"

            row.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=HeadMemberTransactionDetailMenu(
                        member_id=member_id,
                        transaction_id=transaction.id,
                        history_page=current_page,
                        page=page,
                    ).pack(),
                )
            )

        buttons.append(row)

    # Добавляем пагинацию (только если больше одной страницы)
    if total_pages > 1:
        pagination_row = []

        # Первая кнопка (⏪ или пусто)
        if current_page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=HeadMemberGameHistoryMenu(
                        member_id=member_id, history_page=1, page=page
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Вторая кнопка (⬅️ или пусто)
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=HeadMemberGameHistoryMenu(
                        member_id=member_id, history_page=current_page - 1, page=page
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Центральная кнопка - Индикатор страницы
        pagination_row.append(
            InlineKeyboardButton(
                text=f"{current_page}/{total_pages}",
                callback_data="noop",
            )
        )

        # Четвертая кнопка (➡️ или пусто)
        if current_page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=HeadMemberGameHistoryMenu(
                        member_id=member_id, history_page=current_page + 1, page=page
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Пятая кнопка (⏭️ или пусто)
        if current_page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏭️",
                    callback_data=HeadMemberGameHistoryMenu(
                        member_id=member_id, history_page=total_pages, page=page
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Добавляем кнопки навигации
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=HeadMemberGameProfileMenu(
                    member_id=member_id, page=page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def head_member_transaction_detail_kb(
    member_id: int, history_page: int = 1, page: int = 1
) -> InlineKeyboardMarkup:
    """
    Клавиатура для детального просмотра транзакции участника
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=HeadMemberGameHistoryMenu(
                    member_id=member_id, history_page=history_page, page=page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

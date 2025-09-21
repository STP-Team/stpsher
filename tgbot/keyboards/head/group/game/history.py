from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import Sequence

from infrastructure.database.models.STP.transactions import Transaction
from tgbot.keyboards.head.group.game.main import HeadGameMenu
from tgbot.keyboards.head.group.main import GroupManagementMenu
from tgbot.keyboards.user.main import MainMenu


class HeadGroupHistoryMenu(CallbackData, prefix="head_group_history"):
    menu: str = "history"
    page: int = 1


class HeadTransactionDetailMenu(CallbackData, prefix="head_transaction_detail"):
    transaction_id: int
    page: int = 1


class HeadRankingMenu(CallbackData, prefix="head_ranking"):
    menu: str = "ranking"


def head_group_history_kb(
    transactions: Sequence[Transaction],
    current_page: int = 1,
    transactions_per_page: int = 8,
    employee_names: dict = None,
) -> InlineKeyboardMarkup:
    """
    Клавиатура истории транзакций группы для руководителей с пагинацией.
    Отображает 2 транзакции в ряд, по умолчанию 8 транзакций на страницу (4 ряда).

    Args:
        transactions: Список транзакций группы
        current_page: Текущая страница
        transactions_per_page: Количество транзакций на страницу
        employee_names: Словарь user_id -> имя сотрудника
    """
    buttons = []

    if employee_names is None:
        employee_names = {}

    if not transactions:
        # Если нет транзакций, показываем только кнопки навигации
        buttons.append(
            [
                InlineKeyboardButton(
                    text="↩️ Назад",
                    callback_data=GroupManagementMenu(menu="game").pack(),
                ),
                InlineKeyboardButton(
                    text="🏠 Домой",
                    callback_data=MainMenu(menu="main").pack(),
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

        # Получаем имя сотрудника
        employee_name = employee_names.get(transaction.user_id, "Неизвестно")
        if len(employee_name) > 15:
            employee_name = employee_name[:12] + "..."

        button_text = (
            f"{type_emoji} {amount_str} {source_icon} {employee_name} ({date_str})"
        )

        row.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=HeadTransactionDetailMenu(
                    transaction_id=transaction.id, page=current_page
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
            employee_name = employee_names.get(transaction.user_id, "Неизвестно")
            if len(employee_name) > 15:
                employee_name = employee_name[:12] + "..."

            button_text = (
                f"{type_emoji} {amount_str} {source_icon} {employee_name} ({date_str})"
            )

            row.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=HeadTransactionDetailMenu(
                        transaction_id=transaction.id, page=current_page
                    ).pack(),
                )
            )

        buttons.append(row)

    # Добавляем пагинацию (только если больше одной страницы)
    if total_pages > 1:
        pagination_row = []

        # Клавиатура пагинации: [⏪] [⬅️] [страница] [➡️] [⏭️]

        # Первая кнопка (⏪ или пусто)
        if current_page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪", callback_data=HeadGameMenu(menu="history", page=1).pack()
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Вторая кнопка (⬅️ или пусто)
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=HeadGameMenu(
                        menu="history", page=current_page - 1
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Центральная кнопка - Индикатор страницы (всегда видна)
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
                    callback_data=HeadGameMenu(
                        menu="history", page=current_page + 1
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
                    callback_data=HeadGameMenu(menu="history", page=total_pages).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Добавляем кнопки навигации
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=GroupManagementMenu(menu="game").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def head_transaction_detail_kb(page: int = 1) -> InlineKeyboardMarkup:
    """
    Клавиатура для детального просмотра транзакции группы
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data=HeadGameMenu(menu="history", page=page).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой",
                callback_data=MainMenu(menu="main").pack(),
            ),
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

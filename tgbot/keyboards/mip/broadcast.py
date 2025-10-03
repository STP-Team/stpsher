from typing import List, Tuple

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.group import short_name
from tgbot.keyboards.user.main import MainMenu


class BroadcastMenu(CallbackData, prefix="broadcast"):
    action: str


def broadcast_kb() -> InlineKeyboardMarkup:
    """Клавиатура меню рассылки.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard


def broadcast_type_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа рассылки

    :return: Объект встроенной клавиатуры
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="👥 Всем", callback_data=BroadcastMenu(action="everyone").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="🏢 По подразделению",
                callback_data=BroadcastMenu(action="division").pack(),
            ),
            InlineKeyboardButton(
                text="👔 По группам",
                callback_data=BroadcastMenu(action="groups").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def division_selection_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора подразделения

    :return: Объект встроенной клавиатуры
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="📞 НТП 1", callback_data=BroadcastMenu(action="ntp1").pack()
            ),
            InlineKeyboardButton(
                text="📞 НТП 2", callback_data=BroadcastMenu(action="ntp2").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="💬 НЦК", callback_data=BroadcastMenu(action="nck").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=BroadcastMenu(action="back").pack()
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def heads_selection_kb(
    heads: List[Tuple[str, int]], selected_heads: List[int] = None
) -> InlineKeyboardMarkup:
    """Клавиатура выбора руководителей

    :param heads: Список кортежей (имя, user_id) руководителей
    :param selected_heads: Список ID выбранных руководителей
    :return: Объект встроенной клавиатуры
    """
    if selected_heads is None:
        selected_heads = []

    buttons = []

    # Кнопки руководителей (максимум 2 в ряд)
    for i in range(0, len(heads), 2):
        row = []

        # Первый руководитель в ряду
        head_name, head_id = heads[i]
        is_selected = head_id in selected_heads
        emoji = "✅" if is_selected else "☑️"

        row.append(
            InlineKeyboardButton(
                text=f"{emoji} {short_name(head_name)}",
                callback_data=BroadcastMenu(action=f"toggle_head_{head_id}").pack(),
            )
        )

        # Второй руководитель в ряду (если есть)
        if i + 1 < len(heads):
            head_name2, head_id2 = heads[i + 1]
            is_selected2 = head_id2 in selected_heads
            emoji2 = "✅" if is_selected2 else "☑️"

            row.append(
                InlineKeyboardButton(
                    text=f"{emoji2} {short_name(head_name2)}",
                    callback_data=BroadcastMenu(
                        action=f"toggle_head_{head_id2}"
                    ).pack(),
                )
            )

        buttons.append(row)

    # Кнопки управления
    control_buttons = []

    if selected_heads:
        control_buttons.append(
            InlineKeyboardButton(
                text=f"✅ Подтвердить ({len(selected_heads)})",
                callback_data=BroadcastMenu(action="confirm_heads").pack(),
            )
        )

    if control_buttons:
        buttons.append(control_buttons)

    # Кнопка назад
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=BroadcastMenu(action="back").pack()
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirmation_kb() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения рассылки

    :return: Объект встроенной клавиатуры
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=BroadcastMenu(action="confirm").pack(),
            ),
            InlineKeyboardButton(
                text="❌ Отмена", callback_data=BroadcastMenu(action="cancel").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=BroadcastMenu(action="back").pack()
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

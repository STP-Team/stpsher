from collections.abc import Sequence

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infrastructure.database.models.STP.schedule_log import ScheduleFilesLog
from tgbot.keyboards.mip.schedule.main import ScheduleMenu
from tgbot.keyboards.user.main import MainMenu


class ScheduleListMenu(CallbackData, prefix="schedule_list"):
    menu: str


def schedule_list_kb() -> InlineKeyboardMarkup:
    """
    Клавиатура меню файлов графиков.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="📁 Локальные файлы",
                callback_data=ScheduleListMenu(menu="local").pack(),
            ),
            InlineKeyboardButton(
                text="📜 История загрузок",
                callback_data=ScheduleListMenu(menu="history").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=MainMenu(menu="schedule").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard


def list_db_files_kb(
    schedule_files: Sequence[ScheduleFilesLog],
) -> InlineKeyboardMarkup:
    """
    Клавиатура меню файлов графиков в базе данных.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = []
    for file in schedule_files:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"📥 {file.file_name or 'Unknown'} {file.uploaded_at.strftime('%H:%M:%S %d.%m.%y')}",
                    callback_data=f"download_db:{file.id}",
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Назад", callback_data=ScheduleMenu(menu="list").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard


def list_local_files_kb(
    schedule_files: list[str],
) -> InlineKeyboardMarkup:
    """
    Клавиатура меню файлов графиков локальных файлов.

    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = []
    for file in schedule_files:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"📥 {file}",
                    callback_data=f"send_local:{file}",
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Назад", callback_data=ScheduleMenu(menu="list").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard


def schedule_list_back_kb() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=ScheduleMenu(menu="list").pack()
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ]
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard

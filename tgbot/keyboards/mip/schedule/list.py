from collections.abc import Sequence

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infrastructure.database.models.STP.schedule_log import ScheduleFilesLog
from tgbot.keyboards.user.main import MainMenu


class ScheduleHistoryMenu(CallbackData, prefix="schedule_history"):
    menu: str = "history"
    page: int = 1


class ScheduleFileDetailMenu(CallbackData, prefix="schedule_file_detail"):
    file_id: int
    page: int = 1


class ScheduleFileActionMenu(CallbackData, prefix="schedule_file_action"):
    file_id: int
    action: str  # "restore" or "back"
    page: int = 1


class LocalFilesMenu(CallbackData, prefix="local_files"):
    menu: str = "local"
    page: int = 1


class LocalFileDetailMenu(CallbackData, prefix="local_file_detail"):
    file_index: int
    page: int = 1


class LocalFileActionMenu(CallbackData, prefix="local_file_action"):
    file_index: int
    action: str  # "delete", "rename", or "back"
    page: int = 1


def list_db_files_paginated_kb(
    current_page: int, total_pages: int, page_files: Sequence[ScheduleFilesLog] = None
) -> InlineKeyboardMarkup:
    """
    Клавиатура пагинации для файлов графиков в базе данных с кнопками выбора файлов.
    """
    buttons = []

    # Добавляем кнопки для выбора файлов (максимум 2 в ряд)
    if page_files:
        # Вычисляем стартовый индекс для нумерации на текущей странице
        start_idx = (current_page - 1) * 5  # 5 файлов на страницу

        for i in range(0, len(page_files), 2):
            file_row = []

            # Первый файл в ряду
            first_file = page_files[i]
            first_file_number = start_idx + i + 1
            file_row.append(
                InlineKeyboardButton(
                    text=f"{first_file_number}. {first_file.file_name or 'Unknown'}",
                    callback_data=ScheduleFileDetailMenu(
                        file_id=first_file.id, page=current_page
                    ).pack(),
                )
            )

            # Второй файл в ряду (если есть)
            if i + 1 < len(page_files):
                second_file = page_files[i + 1]
                second_file_number = start_idx + i + 2
                file_row.append(
                    InlineKeyboardButton(
                        text=f"{second_file_number}. {second_file.file_name or 'Unknown'}",
                        callback_data=ScheduleFileDetailMenu(
                            file_id=second_file.id, page=current_page
                        ).pack(),
                    )
                )

            buttons.append(file_row)

    # Пагинация
    if total_pages > 1:
        pagination_row = []

        # Первая кнопка (⏪ или пусто)
        if current_page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=ScheduleHistoryMenu(menu="history", page=1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Вторая кнопка (⬅️ или пусто)
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=ScheduleHistoryMenu(
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
                    callback_data=ScheduleHistoryMenu(
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
                    callback_data=ScheduleHistoryMenu(
                        menu="history", page=total_pages
                    ).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Навигация
    navigation_row = [
        InlineKeyboardButton(
            text="🔙 Назад", callback_data=MainMenu(menu="schedule").pack()
        ),
        InlineKeyboardButton(
            text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
        ),
    ]
    buttons.append(navigation_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def list_db_files_kb(
    schedule_files: Sequence[ScheduleFilesLog],
) -> InlineKeyboardMarkup:
    """
    Клавиатура меню файлов графиков в базе данных (legacy compatibility).

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
                text="🔙 Назад", callback_data=MainMenu(menu="schedule").pack()
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


def list_local_files_paginated_kb(
    current_page: int,
    total_pages: int,
    page_files: list[str] = None,
    all_files: list[str] = None,
) -> InlineKeyboardMarkup:
    """
    Пагинированная клавиатура для локальных файлов графиков с кнопками выбора файлов.
    """
    buttons = []

    # Добавляем кнопки для выбора файлов (максимум 2 в ряд)
    if page_files and all_files:
        # Вычисляем стартовый индекс для нумерации на текущей странице
        start_idx = (current_page - 1) * 5  # 5 файлов на страницу

        for i in range(0, len(page_files), 2):
            file_row = []

            # Первый файл в ряду
            first_file = page_files[i]
            first_file_number = start_idx + i + 1
            first_file_index = all_files.index(first_file)

            # Truncate filename for display if too long
            display_name = (
                first_file if len(first_file) <= 25 else first_file[:22] + "..."
            )

            file_row.append(
                InlineKeyboardButton(
                    text=f"{first_file_number}. {display_name}",
                    callback_data=LocalFileDetailMenu(
                        file_index=first_file_index, page=current_page
                    ).pack(),
                )
            )

            # Второй файл в ряду (если есть)
            if i + 1 < len(page_files):
                second_file = page_files[i + 1]
                second_file_number = start_idx + i + 2
                second_file_index = all_files.index(second_file)

                # Truncate filename for display if too long
                display_name = (
                    second_file if len(second_file) <= 25 else second_file[:22] + "..."
                )

                file_row.append(
                    InlineKeyboardButton(
                        text=f"{second_file_number}. {display_name}",
                        callback_data=LocalFileDetailMenu(
                            file_index=second_file_index, page=current_page
                        ).pack(),
                    )
                )

            buttons.append(file_row)

    # Пагинация
    if total_pages > 1:
        pagination_row = []

        # Первая кнопка (⏪ или пусто)
        if current_page > 2:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⏪",
                    callback_data=LocalFilesMenu(menu="local", page=1).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        # Вторая кнопка (⬅️ или пусто)
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=LocalFilesMenu(
                        menu="local", page=current_page - 1
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
                    callback_data=LocalFilesMenu(
                        menu="local", page=current_page + 1
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
                    callback_data=LocalFilesMenu(menu="local", page=total_pages).pack(),
                )
            )
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        buttons.append(pagination_row)

    # Навигация
    navigation_row = [
        InlineKeyboardButton(
            text="🔙 Назад", callback_data=MainMenu(menu="schedule").pack()
        ),
        InlineKeyboardButton(
            text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
        ),
    ]
    buttons.append(navigation_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def list_local_files_kb(
    schedule_files: list[str],
) -> InlineKeyboardMarkup:
    """
    Клавиатура меню файлов графиков локальных файлов (legacy compatibility).

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
                text="🔙 Назад", callback_data=MainMenu(menu="schedule").pack()
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


def schedule_file_detail_kb(file_id: int, page: int) -> InlineKeyboardMarkup:
    """
    Клавиатура детального просмотра файла с возможностью восстановления.
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="💾 Восстановить файл",
                callback_data=ScheduleFileActionMenu(
                    file_id=file_id, action="restore", page=page
                ).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="📥 Скачать файл",
                callback_data=f"download_db:{file_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="↩️ К списку",
                callback_data=ScheduleHistoryMenu(menu="history", page=page).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def local_file_detail_kb(
    file_index: int, filename: str, page: int
) -> InlineKeyboardMarkup:
    """
    Клавиатура детального просмотра локального файла с возможностью удаления и переименования.
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✏️ Переименовать",
                callback_data=LocalFileActionMenu(
                    file_index=file_index, action="rename", page=page
                ).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Удалить",
                callback_data=LocalFileActionMenu(
                    file_index=file_index, action="delete", page=page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="📥 Скачать",
                callback_data=f"send_local:{filename}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="↩️ К списку",
                callback_data=LocalFilesMenu(menu="local", page=page).pack(),
            ),
            InlineKeyboardButton(
                text="🏠 Домой", callback_data=MainMenu(menu="main").pack()
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def schedule_list_back_kb() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="🔙 Назад", callback_data=MainMenu(menu="schedule").pack()
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

"""Обработчики для функций файлов."""

import logging
from pathlib import Path

from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Select

from tgbot.dialogs.states.common.files import Files

logger = logging.getLogger(__name__)


async def start_upload_dialog(
    _callback: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик перехода в диалог файлов.

    Args:
        _callback: Callback query от Telegram
        _widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.start(
        Files.menu,
    )


async def close_files_dialog(
    _callback: CallbackQuery,
    _button: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик возврата к главному диалогу из диалога файлов.

    Args:
        _callback: Callback query от пользователя
        _button: Button виджет
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.done()


async def on_file_selected(
    _callback: CallbackQuery,
    _widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Обработчик выбора файла из списка.

    Args:
        _callback: Callback query от пользователя
        _widget: Select виджет
        dialog_manager: Менеджер диалога
        item_id: ID выбранного файла (имя файла)
    """
    dialog_manager.dialog_data["selected_file"] = item_id
    await dialog_manager.switch_to(Files.local_details)


async def on_remove_file(
    _callback: CallbackQuery,
    _button: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик удаления файла.

    Args:
        _callback: Callback query от пользователя
        _button: Button виджет
        dialog_manager: Менеджер диалога
    """
    file_name = dialog_manager.dialog_data.get("selected_file")
    if not file_name:
        await _callback.answer("Файл не выбран", show_alert=True)
        return

    file_path = Path("uploads") / file_name
    if file_path.exists():
        file_path.unlink()
        await _callback.answer(f"Файл {file_name} удалён", show_alert=True)
        await dialog_manager.switch_to(Files.local)
    else:
        await _callback.answer("Файл не найден", show_alert=True)


async def on_rename_file(
    _callback: CallbackQuery,
    _button: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик начала переименования файла.

    Args:
        _callback: Callback query от пользователя
        _button: Button виджет
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.switch_to(Files.rename)


async def process_rename(
    _message: Message,
    _widget: TextInput,
    dialog_manager: DialogManager,
    new_name: str,
) -> None:
    """Обработчик ввода нового имени файла.

    Args:
        _message: Сообщение от пользователя
        _widget: TextInput виджет
        dialog_manager: Менеджер диалога
        new_name: Новое имя файла
    """
    file_name = dialog_manager.dialog_data.get("selected_file")
    if not file_name:
        return

    old_path = Path("uploads") / file_name
    if not old_path.exists():
        return

    new_path = Path("uploads") / new_name
    old_path.rename(new_path)

    dialog_manager.dialog_data["selected_file"] = new_name
    await dialog_manager.switch_to(Files.local_details)


async def on_restore_selected(
    _callback: CallbackQuery,
    _widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Обработчик восстановления выбранного файла из истории.

    Args:
        _callback: Callback query от пользователя
        _widget: Select виджет
        dialog_manager: Менеджер диалога
        item_id: database record id
    """
    bot: Bot = dialog_manager.middleware_data.get("bot")
    file_name = dialog_manager.dialog_data.get("selected_file")

    if not bot or not file_name:
        await _callback.answer("Ошибка восстановления", show_alert=True)
        return

    # Получаем file_id из истории по record id
    history = dialog_manager.dialog_data.get("history", [])
    file_id = None
    for record in history:
        if str(record[0]) == str(item_id):  # record[0] - database id
            file_id = record[5]  # record[5] - Telegram file_id
            break

    if not file_id:
        await _callback.answer("Файл не найден в истории", show_alert=True)
        return

    try:
        # Скачиваем файл из Telegram
        file = await bot.get_file(file_id)
        file_path = Path("uploads") / file_name
        await bot.download_file(file.file_path, file_path)

        await _callback.answer(f"Файл {file_name} восстановлен", show_alert=True)
        await dialog_manager.switch_to(Files.local_details)
    except Exception as e:
        logger.error(f"Ошибка восстановления файла: {e}")
        await _callback.answer("Не удалось восстановить файл", show_alert=True)


async def on_history_file_selected(
    _callback: CallbackQuery,
    _widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Обработчик выбора файла из истории загрузок.

    Args:
        _callback: Callback query от пользователя
        _widget: Select виджет
        dialog_manager: Менеджер диалога
        item_id: ID выбранного файла (database record id)
    """
    dialog_manager.dialog_data["selected_history_file"] = item_id
    await dialog_manager.switch_to(Files.history_details)


async def on_download_local_file(
    _callback: CallbackQuery,
    _button: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик скачивания локального файла.

    Args:
        _callback: Callback query от пользователя
        _button: Button виджет
        dialog_manager: Менеджер диалога
    """
    bot: Bot = dialog_manager.middleware_data.get("bot")
    file_name = dialog_manager.dialog_data.get("selected_file")

    if not bot or not file_name:
        await _callback.answer("Ошибка скачивания", show_alert=True)
        return

    file_path = Path("uploads") / file_name

    if not file_path.exists():
        await _callback.answer("Файл не найден", show_alert=True)
        return

    try:
        from aiogram.types import FSInputFile

        file = FSInputFile(file_path)
        await bot.send_document(_callback.from_user.id, file)
        await _callback.answer("Файл отправлен", show_alert=False)
    except Exception as e:
        logger.error(f"Ошибка отправки файла: {e}")
        await _callback.answer("Не удалось отправить файл", show_alert=True)


async def on_download_history_file(
    _callback: CallbackQuery,
    _button: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик скачивания файла из истории.

    Args:
        _callback: Callback query от пользователя
        _button: Button виджет
        dialog_manager: Менеджер диалога
    """
    bot: Bot = dialog_manager.middleware_data.get("bot")
    history_file_id = dialog_manager.dialog_data.get("selected_history_file")

    if not bot or not history_file_id:
        await _callback.answer("Ошибка скачивания", show_alert=True)
        return

    # Получаем информацию о файле из dialog_data
    from tgbot.dialogs.getters.common.files import get_history_file_details

    stp_repo = dialog_manager.middleware_data.get("stp_repo")
    file_info_data = await get_history_file_details(
        stp_repo=stp_repo, dialog_manager=dialog_manager
    )
    file_info = file_info_data.get("file_info")

    if not file_info or not file_info.get("file_id"):
        await _callback.answer("Файл не найден", show_alert=True)
        return

    try:
        await bot.send_document(
            _callback.from_user.id, file_info["file_id"], caption=file_info["name"]
        )
        await _callback.answer("Файл отправлен", show_alert=False)
    except Exception as e:
        logger.error(f"Ошибка отправки файла: {e}")
        await _callback.answer("Не удалось отправить файл", show_alert=True)


async def on_restore_history_file(
    _callback: CallbackQuery,
    _button: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик восстановления файла из истории в локальную папку.

    Args:
        _callback: Callback query от пользователя
        _button: Button виджет
        dialog_manager: Менеджер диалога
    """
    bot: Bot = dialog_manager.middleware_data.get("bot")
    history_file_id = dialog_manager.dialog_data.get("selected_history_file")

    if not bot or not history_file_id:
        await _callback.answer("Ошибка восстановления", show_alert=True)
        return

    # Получаем информацию о файле из dialog_data
    from tgbot.dialogs.getters.common.files import get_history_file_details

    stp_repo = dialog_manager.middleware_data.get("stp_repo")
    file_info_data = await get_history_file_details(
        stp_repo=stp_repo, dialog_manager=dialog_manager
    )
    file_info = file_info_data.get("file_info")

    if not file_info or not file_info.get("file_id"):
        await _callback.answer("Файл не найден", show_alert=True)
        return

    try:
        # Скачиваем файл из Telegram
        file = await bot.get_file(file_info["file_id"])
        file_path = Path("uploads") / file_info["name"]
        await bot.download_file(file.file_path, file_path)

        await _callback.answer(
            f"Файл {file_info['name']} восстановлен", show_alert=True
        )
        await dialog_manager.switch_to(Files.history)
    except Exception as e:
        logger.error(f"Ошибка восстановления файла: {e}")
        await _callback.answer("Не удалось восстановить файл", show_alert=True)

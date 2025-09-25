import os
from datetime import datetime

import pytz
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import MipFilter
from tgbot.keyboards.mip.schedule.list import (
    FileVersionSelectMenu,
    FileVersionsMenu,
    LocalFileActionMenu,
    LocalFileDetailMenu,
    LocalFilesMenu,
    RestoreConfirmMenu,
    ScheduleFileActionMenu,
    ScheduleFileDetailMenu,
    ScheduleHistoryMenu,
    file_versions_list_kb,
    list_db_files_paginated_kb,
    list_local_files_paginated_kb,
    local_file_detail_kb,
    restore_confirmation_kb,
    schedule_file_detail_kb,
    schedule_list_back_kb,
)
from tgbot.keyboards.mip.schedule.main import ScheduleMenu
from tgbot.misc.states.mip.schedule import RenameLocalFile

mip_list_router = Router()
mip_list_router.message.filter(F.chat.type == "private", MipFilter())
mip_list_router.callback_query.filter(F.message.chat.type == "private", MipFilter())


def to_ekaterinburg_time(utc_dt: datetime, format_type: str = "short") -> str:
    """Convert UTC datetime to Ekaterinburg timezone and format it"""
    ekb_tz = pytz.timezone("Asia/Yekaterinburg")

    # If datetime is naive (no timezone info), assume it's UTC
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)

    # Convert to Ekaterinburg time
    ekb_time = utc_dt.astimezone(ekb_tz)

    if format_type == "long":
        return ekb_time.strftime("%d.%m.%Y в %H:%M:%S")
    else:
        return ekb_time.strftime("%H:%M:%S %d.%m.%y")


@mip_list_router.callback_query(ScheduleMenu.filter(F.menu == "local"))
async def show_local_files(callback: CallbackQuery):
    """Handler for initial local files view"""
    await show_local_files_paginated(
        callback=callback,
        callback_data=LocalFilesMenu(menu="local", page=1),
    )


@mip_list_router.callback_query(LocalFilesMenu.filter())
async def show_local_files_paginated(
    callback: CallbackQuery = None,
    callback_data: LocalFilesMenu = None,
    message: Message = None,
):
    """Paginated handler for local files view"""
    page = callback_data.page

    # Get all local files
    local_files = next(os.walk("uploads"), (None, None, []))[2]
    local_files = sorted(local_files)  # Sort alphabetically

    if not local_files:
        text = """<b>📁 Локальные файлы</b>
        
Сейчас на сервер ничего не загружено :("""
        markup = schedule_list_back_kb()

        if callback:
            await callback.message.edit_text(text, reply_markup=markup)
        elif message:
            await message.answer(text, reply_markup=markup)
        return

    # Pagination logic
    files_per_page = 5
    total_files = len(local_files)
    total_pages = (total_files + files_per_page - 1) // files_per_page

    # Calculate start and end for current page
    start_idx = (page - 1) * files_per_page
    end_idx = start_idx + files_per_page
    page_files = local_files[start_idx:end_idx]

    # Build file list for current page
    files_info = []
    for counter, filename in enumerate(page_files, start=start_idx + 1):
        file_path = os.path.join("uploads", filename)
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        size_mb = round(file_size / (1024 * 1024), 2)

        files_info.append(f"{counter}. <b>{filename}</b>")
        files_info.append(f"📊 Размер: {size_mb} MB")
        files_info.append("")

    files_text = "\n".join(files_info)
    message_text = f"""<b>📁 Локальные файлы</b>

{files_text}
<i>Нажми на файл для подробной информации</i>"""

    markup = list_local_files_paginated_kb(page, total_pages, page_files, local_files)

    if callback:
        await callback.message.edit_text(message_text, reply_markup=markup)
    elif message:
        await message.answer(message_text, reply_markup=markup)


@mip_list_router.callback_query(ScheduleMenu.filter(F.menu == "history"))
async def show_history_files(callback: CallbackQuery, stp_repo: MainRequestsRepo):
    """Handler for initial history files view"""
    await show_history_files_paginated(
        callback=callback,
        callback_data=ScheduleHistoryMenu(menu="history", page=1),
        stp_repo=stp_repo,
    )


@mip_list_router.callback_query(ScheduleHistoryMenu.filter())
async def show_history_files_paginated(
    callback: CallbackQuery,
    callback_data: ScheduleHistoryMenu,
    stp_repo: MainRequestsRepo,
):
    """Paginated handler for history files view"""
    page = callback_data.page

    # Get all files sorted by upload date (newest first)
    all_files = await stp_repo.upload.get_files_history()
    all_files = sorted(all_files, key=lambda x: x.uploaded_at, reverse=True)

    if not all_files:
        await callback.message.edit_text(
            """<b>📜 История загрузок</b>
        
История загрузок пуста :(""",
            reply_markup=schedule_list_back_kb(),
        )
        return

    # Pagination logic
    files_per_page = 5
    total_files = len(all_files)
    total_pages = (total_files + files_per_page - 1) // files_per_page

    # Calculate start and end for current page
    start_idx = (page - 1) * files_per_page
    end_idx = start_idx + files_per_page
    page_files = all_files[start_idx:end_idx]

    # Build file list for current page
    files_info = []
    for counter, file in enumerate(page_files, start=start_idx + 1):
        user = await stp_repo.employee.get_user(user_id=file.uploaded_by_user_id)

        ekb_time = to_ekaterinburg_time(file.uploaded_at)
        if user.username:
            files_info.append(
                f"""{counter}. <b>{file.file_name or "Unknown"}</b>
Загрузил: <a href='t.me/{user.username}'>{user.fullname}</a> в {ekb_time}
Размер файла: {round(file.file_size / (1024 * 1024), 2)} MB"""
            )
        else:
            files_info.append(
                f"""{counter}. <b>{file.file_name or "Unknown"}</b>
Загрузил: <a href='tg://user?id={user.user_id}'>{user.fullname}</a> в {ekb_time}
Размер файла: {round(file.file_size / (1024 * 1024), 2)} MB"""
            )
        files_info.append("")

    files_text = "\n".join(files_info)
    message_text = f"""<b>📜 История загрузок</b>

{files_text}
<i>Используй меню для просмотра подробной информации о файле</i>"""

    await callback.message.edit_text(
        message_text,
        reply_markup=list_db_files_paginated_kb(page, total_pages, page_files),
    )


@mip_list_router.callback_query(F.data.startswith("send_local:"))
async def send_local_file(callback: CallbackQuery):
    filename = callback.data.split(":", 1)[1]
    filepath = os.path.join("uploads", filename)

    try:
        if os.path.exists(filepath):
            await callback.message.answer_document(
                document=FSInputFile(filepath, filename=filename)
            )
            await callback.answer("Файл отправлен!")
        else:
            await callback.answer("Файл не найден", show_alert=True)
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}", show_alert=True)


@mip_list_router.callback_query(ScheduleFileDetailMenu.filter())
async def show_file_detail(
    callback: CallbackQuery,
    callback_data: ScheduleFileDetailMenu,
    stp_repo: MainRequestsRepo,
):
    """Handler for detailed file information view"""
    file_id = callback_data.file_id
    page = callback_data.page

    try:
        logs = await stp_repo.upload.get_files_history()
        file_log = next((log for log in logs if log.id == file_id), None)

        if not file_log:
            await callback.message.edit_text(
                """<b>📝 Подробно о файле</b>
        
Файл не найден ☹""",
                reply_markup=schedule_list_back_kb(),
            )
            return

        user = await stp_repo.employee.get_user(user_id=file_log.uploaded_by_user_id)

        # Check if file exists locally
        local_exists = os.path.exists(
            os.path.join("uploads", file_log.file_name or "unknown")
        )
        local_status = (
            "Файл с таким названием есть на сервере"
            if local_exists
            else "Не сохранен на сервере"
        )

        if user.username:
            user_info = f"<a href='t.me/{user.username}'>{user.fullname}</a>"
        else:
            user_info = f"<a href='tg://user?id={user.user_id}'>{user.fullname}</a>"

        ekb_time = to_ekaterinburg_time(file_log.uploaded_at, "long")
        message_text = f"""<b>📝 Подробно о файле</b>

<b>📄 Название</b>
{file_log.file_name or "Unknown"}

<b>🤨 Загрузил</b>
{user_info}

<b>📅 Дата загрузки</b>
{ekb_time}

<b>🏋 Размер файла</b>
{round(file_log.file_size / (1024 * 1024), 2)} MB

<b>💾 Статус на сервере</b>
{local_status}"""

        await callback.message.edit_text(
            message_text,
            reply_markup=schedule_file_detail_kb(file_id, page),
        )

    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}", show_alert=True)


@mip_list_router.callback_query(ScheduleFileActionMenu.filter())
async def handle_file_action(
    callback: CallbackQuery,
    callback_data: ScheduleFileActionMenu,
    stp_repo: MainRequestsRepo,
):
    """Handler for file actions (restore/back)"""
    file_id = callback_data.file_id
    action = callback_data.action
    page = callback_data.page

    if action == "restore":
        try:
            logs = await stp_repo.upload.get_files_history()
            file_log = next((log for log in logs if log.id == file_id), None)

            if not file_log:
                await callback.answer("Файл не найден", show_alert=True)
                return

            filename = file_log.file_name or f"file_{file_id}"
            filepath = os.path.join("uploads", filename)

            # Download file from Telegram and save to uploads folder
            file_info = await callback.bot.get_file(file_log.file_id)
            await callback.bot.download_file(file_info.file_path, filepath)

            await callback.answer(
                f"✅ Файл '{filename}' успешно восстановлен на сервер!", show_alert=True
            )

            # Refresh the file detail view to show updated status
            await show_file_detail(
                callback=callback,
                callback_data=ScheduleFileDetailMenu(file_id=file_id, page=page),
                stp_repo=stp_repo,
            )

        except Exception as e:
            await callback.answer(
                f"Ошибка при восстановлении: {str(e)}", show_alert=True
            )

    elif action == "back":
        # Return to files list
        await show_history_files_paginated(
            callback=callback,
            callback_data=ScheduleHistoryMenu(menu="history", page=page),
            stp_repo=stp_repo,
        )


@mip_list_router.callback_query(F.data.startswith("download_db:"))
async def download_db_file(callback: CallbackQuery, stp_repo: MainRequestsRepo):
    log_id = int(callback.data.split(":")[1])

    try:
        logs = await stp_repo.upload.get_files_history()
        log = next((log for log in logs if log.id == log_id), None)

        if not log:
            await callback.answer("Файл не найден", show_alert=True)
            return

        await callback.message.answer_document(document=log.file_id)
        await callback.answer("Файл отправлен!")
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}", show_alert=True)


@mip_list_router.callback_query(LocalFileDetailMenu.filter())
async def show_local_file_detail(
    callback: CallbackQuery,
    callback_data: LocalFileDetailMenu,
    stp_repo: MainRequestsRepo,
):
    """Handler for detailed local file information view"""
    file_index = callback_data.file_index
    page = callback_data.page

    try:
        # Get all local files to map index back to filename
        local_files = next(os.walk("uploads"), (None, None, []))[2]
        local_files = sorted(local_files)

        if file_index >= len(local_files):
            await callback.message.edit_text(
                """<b>📝 Подробно о файле</b>
        
Файл не найден ☹""",
                reply_markup=schedule_list_back_kb(),
            )
            return

        filename = local_files[file_index]
        file_path = os.path.join("uploads", filename)

        if not os.path.exists(file_path):
            await callback.message.edit_text(
                """<b>📝 Подробно о файле</b>
        
Файл не найден ☹""",
                reply_markup=schedule_list_back_kb(),
            )
            return

        # Get file size
        file_size = os.path.getsize(file_path)
        size_mb = round(file_size / (1024 * 1024), 2)

        # Get file modification time
        mod_time = os.path.getmtime(file_path)
        mod_datetime = datetime.fromtimestamp(mod_time)

        # Try to get info from schedule_log for this filename
        logs = await stp_repo.upload.get_files_history()
        file_log = None
        uploader_info = "Неизвестно"
        upload_date = "Неизвестно"

        # Clean filename for matching
        clean_filename = filename
        if filename.startswith("temp_current_"):
            clean_filename = filename[13:]

        # Find the most recent log entry for this filename (try both original and clean names)
        for log in sorted(logs, key=lambda x: x.uploaded_at, reverse=True):
            if log.file_name == filename or log.file_name == clean_filename:
                file_log = log
                break

        if file_log:
            uploader = await stp_repo.employee.get_user(
                user_id=file_log.uploaded_by_user_id
            )
            if uploader:
                if uploader.username:
                    uploader_info = (
                        f"<a href='t.me/{uploader.username}'>{uploader.fullname}</a>"
                    )
                else:
                    uploader_info = f"<a href='tg://user?id={uploader.user_id}'>{uploader.fullname}</a>"
            upload_date = to_ekaterinburg_time(file_log.uploaded_at, "long")

        # Convert local file modification time to Ekaterinburg timezone
        local_mod_time = to_ekaterinburg_time(mod_datetime, "long")

        message_text = f"""<b>📝 Подробно о файле</b>

<b>📄 Название</b>
{filename}

<b>🏋 Размер файла</b>
{size_mb} MB

<b>📅 Дата последнего изменения на сервере</b>
{local_mod_time}

<b>🤨 Последний загрузивший</b>
{uploader_info}

<b>📅 Дата первой загрузки</b>
{upload_date}"""

        # Add warning for temp_current_ files
        if filename.startswith("temp_current_"):
            message_text += f"""

⚠️ <b>Устаревший файл</b>
Этот файл имеет префикс 'temp_current_' и может быть устаревшим.
Рекомендуется удалить его, если есть более новая версия без префикса:
<code>{clean_filename}</code>"""

        await callback.message.edit_text(
            message_text,
            reply_markup=local_file_detail_kb(file_index, filename, page),
        )

    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}", show_alert=True)


@mip_list_router.callback_query(LocalFileActionMenu.filter())
async def handle_local_file_action(
    callback: CallbackQuery,
    callback_data: LocalFileActionMenu,
    state: FSMContext,
    stp_repo: MainRequestsRepo,
):
    """Handler for local file actions (delete/rename/recover/back)"""
    file_index = callback_data.file_index
    action = callback_data.action
    page = callback_data.page

    try:
        # Get all local files to map index back to filename
        local_files = next(os.walk("uploads"), (None, None, []))[2]
        local_files = sorted(local_files)

        if file_index >= len(local_files):
            await callback.answer("Файл не найден", show_alert=True)
            return

        filename = local_files[file_index]

    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}", show_alert=True)
        return

    if action == "recover":
        # Start the file recovery process
        await show_file_versions(callback, filename, page, stp_repo, 1)
        return

    elif action == "delete":
        try:
            file_path = os.path.join("uploads", filename)

            if not os.path.exists(file_path):
                await callback.answer("Файл не найден", show_alert=True)
                return

            # Delete the file
            os.remove(file_path)

            await callback.answer(
                f"✅ Файл '{filename}' успешно удален!", show_alert=True
            )

            # Return to files list
            await show_local_files_paginated(
                callback=callback,
                callback_data=LocalFilesMenu(menu="local", page=page),
            )

        except Exception as e:
            await callback.answer(f"Ошибка при удалении: {str(e)}", show_alert=True)

    elif action == "rename":
        # Start rename process by setting state and storing file info
        await callback.message.edit_text(
            f"""<b>📝 Переименование файла</b>

<b>Текущее название:</b>
{filename}

Введите новое название файла:""",
            reply_markup=schedule_list_back_kb(),
        )

        # Set state and store file info
        await state.set_state(RenameLocalFile.waiting_new_filename)
        await state.update_data(file_index=file_index, old_filename=filename, page=page)

    elif action == "back":
        # Return to files list
        await show_local_files_paginated(
            callback=callback,
            callback_data=LocalFilesMenu(menu="local", page=page),
        )


@mip_list_router.message(RenameLocalFile.waiting_new_filename)
async def process_new_filename(message: Message, state: FSMContext):
    """Handler for processing new filename input"""
    try:
        # Get state data
        data = await state.get_data()
        old_filename = data.get("old_filename")
        page = data.get("page")

        new_filename = message.text.strip()

        # Validate new filename
        if not new_filename:
            await message.answer(
                "❌ Название файла не может быть пустым. Попробуйте еще раз:"
            )
            return

        # Check for invalid characters
        invalid_chars = ["<", ">", ":", '"', "|", "?", "*", "/", "\\"]
        if any(char in new_filename for char in invalid_chars):
            await message.answer(
                f"❌ Название файла содержит недопустимые символы: {', '.join(invalid_chars)}\\n"
                "Попробуйте еще раз:"
            )
            return

        # Check if file with new name already exists
        new_filepath = os.path.join("uploads", new_filename)
        if os.path.exists(new_filepath):
            await message.answer(
                f"❌ Файл с названием '{new_filename}' уже существует.\\n"
                "Выбери другое название:"
            )
            return

        # Perform rename
        old_filepath = os.path.join("uploads", old_filename)

        if not os.path.exists(old_filepath):
            await message.answer("❌ Исходный файл не найден")
            await state.clear()
            return

        os.rename(old_filepath, new_filepath)

        await message.answer(
            f"✅ Файл успешно переименован:\n<code>{old_filename}</code> → <code>{new_filename}</code>"
        )

        # Clear state
        await state.clear()

        # Show updated file list
        await show_local_files_paginated(
            callback=None,
            callback_data=LocalFilesMenu(menu="local", page=page),
            message=message,
        )

    except Exception as e:
        await message.answer(f"❌ Ошибка при переименовании: {str(e)}")
        await state.clear()


async def show_file_versions(
    callback: CallbackQuery,
    filename: str,
    stp_repo: MainRequestsRepo,
    versions_page: int = 1,
):
    """Show paginated list of available versions of a file for recovery"""
    try:
        # Clean filename for matching
        clean_filename = filename
        if filename.startswith("temp_current_"):
            clean_filename = filename[13:]

        # Get all versions of this file
        logs = await stp_repo.upload.get_files_history()
        all_file_versions = []

        for log in logs:
            if log.file_name == filename or log.file_name == clean_filename:
                all_file_versions.append(log)

        # Sort by upload date (newest first)
        all_file_versions = sorted(
            all_file_versions, key=lambda x: x.uploaded_at, reverse=True
        )

        if not all_file_versions:
            await callback.message.edit_text(
                f"""<b>⏪ Восстановление файла</b>

<b>Файл:</b> {filename}

❌ Для этого файла не найдено версий в истории загрузок.
Возможно, файл был создан локально или загружен до внедрения системы логирования.""",
                reply_markup=schedule_list_back_kb(),
            )
            return

        # Pagination logic for versions
        versions_per_page = 8
        total_versions = len(all_file_versions)
        total_pages = (total_versions + versions_per_page - 1) // versions_per_page

        # Calculate start and end for current versions page
        start_idx = (versions_page - 1) * versions_per_page
        end_idx = start_idx + versions_per_page
        page_versions = all_file_versions[start_idx:end_idx]

        message_text = f"""<b>⏪ Восстановление файла</b>

<b>Файл:</b> {filename}
<b>Найдено версий:</b> {total_versions}

<i>Выбери версию для восстановления:</i>"""

        await callback.message.edit_text(
            message_text,
            reply_markup=file_versions_list_kb(
                page_versions, filename, versions_page, total_pages
            ),
        )

    except Exception as e:
        await callback.answer(
            f"Ошибка при получении версий файла: {str(e)}", show_alert=True
        )


@mip_list_router.callback_query(FileVersionsMenu.filter())
async def handle_file_versions_pagination(
    callback: CallbackQuery, callback_data: FileVersionsMenu, stp_repo: MainRequestsRepo
):
    """Handler for file versions pagination"""
    filename = callback_data.filename
    versions_page = callback_data.page

    await show_file_versions(callback, filename, 1, stp_repo, versions_page)


@mip_list_router.callback_query(FileVersionSelectMenu.filter())
async def handle_version_selection(
    callback: CallbackQuery,
    callback_data: FileVersionSelectMenu,
    stp_repo: MainRequestsRepo,
):
    """Handler for version selection confirmation"""
    file_id = callback_data.file_id
    filename = callback_data.filename
    page = callback_data.page

    try:
        # Get version info
        logs = await stp_repo.upload.get_files_history()
        selected_version = next((log for log in logs if log.id == file_id), None)

        if not selected_version:
            await callback.answer("Версия файла не найдена", show_alert=True)
            return

        uploader = await stp_repo.employee.get_user(
            user_id=selected_version.uploaded_by_user_id
        )
        uploader_name = uploader.fullname if uploader else "Неизвестно"
        upload_time = to_ekaterinburg_time(selected_version.uploaded_at, "long")
        size_mb = round(selected_version.file_size / (1024 * 1024), 2)

        # Show confirmation message
        message_text = f"""<b>🔄 Подтверждение восстановления</b>

<b>Файл:</b> {filename}
<b>Выбранная версия:</b> {upload_time}
<b>Загружена:</b> <a href='t.me/{uploader.username}'>{uploader_name}</a>
<b>Размер:</b> {size_mb} MB

⚠️ <b>ВНИМАНИЕ!</b>
Текущий файл будет заменен выбранной версией.
Это действие необратимо.

Продолжить восстановление?"""

        await callback.message.edit_text(
            message_text, reply_markup=restore_confirmation_kb(file_id, filename, page)
        )

    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}", show_alert=True)


@mip_list_router.callback_query(RestoreConfirmMenu.filter())
async def handle_restore_confirmation(
    callback: CallbackQuery,
    callback_data: RestoreConfirmMenu,
    stp_repo: MainRequestsRepo,
):
    """Handler for restore confirmation"""
    file_id = callback_data.file_id
    filename = callback_data.filename
    action = callback_data.action

    if action == "cancel":
        # Return to local files list (page 1)
        await show_local_files_paginated(
            callback=callback, callback_data=LocalFilesMenu(menu="local", page=1)
        )
        return

    elif action == "confirm":
        try:
            # Get version info
            logs = await stp_repo.upload.get_files_history()
            selected_version = next((log for log in logs if log.id == file_id), None)

            if not selected_version:
                await callback.answer("Версия файла не найдена", show_alert=True)
                return

            filepath = os.path.join("uploads", filename)

            # Download file from Telegram and save to uploads folder
            file_info = await callback.bot.get_file(selected_version.file_id)
            await callback.bot.download_file(file_info.file_path, filepath)

            await callback.answer(
                f"✅ Файл '{filename}' успешно восстановлен!", show_alert=True
            )

            # Return to local files list (page 1)
            await show_local_files_paginated(
                callback=callback, callback_data=LocalFilesMenu(menu="local", page=1)
            )

        except Exception as e:
            await callback.answer(
                f"Ошибка при восстановлении: {str(e)}", show_alert=True
            )

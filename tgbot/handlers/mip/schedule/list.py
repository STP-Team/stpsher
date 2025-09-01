import os

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import MipFilter
from tgbot.keyboards.mip.schedule.list import (
    list_db_files_paginated_kb,
    schedule_list_back_kb,
    list_local_files_kb,
    ScheduleHistoryMenu,
    ScheduleFileDetailMenu,
    ScheduleFileActionMenu,
    schedule_file_detail_kb,
)
from tgbot.keyboards.mip.schedule.main import ScheduleMenu

mip_list_router = Router()
mip_list_router.message.filter(F.chat.type == "private", MipFilter())
mip_list_router.callback_query.filter(F.message.chat.type == "private", MipFilter())


@mip_list_router.callback_query(ScheduleMenu.filter(F.menu == "local"))
async def show_local_files(callback: CallbackQuery):
    local_files = next(os.walk("uploads"), (None, None, []))[2]

    if not local_files:
        await callback.message.edit_text(
            """<b>📁 Локальные файлы</b>
        
Сейчас на сервер ничего не загружено :(""",
            reply_markup=schedule_list_back_kb(),
        )
        return

    files_text = "\n".join(f"• {file}" for file in local_files)
    await callback.message.edit_text(
        f"<b>📁 Локальные файлы</b>\n\n{files_text}",
        reply_markup=list_local_files_kb(schedule_files=local_files),
    )


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
        user = await stp_repo.user.get_user(user_id=file.uploaded_by_user_id)

        if user.username:
            files_info.append(
                f"""{counter}. <b>{file.file_name or "Unknown"}</b>
Загрузил: <a href='t.me/{user.username}'>{user.fullname}</a> в {file.uploaded_at.strftime("%H:%M:%S %d.%m.%y")}
Размер файла: {round(file.file_size / (1024 * 1024), 2)} MB"""
            )
        else:
            files_info.append(
                f"""{counter}. <b>{file.file_name or "Unknown"}</b>
Загрузил: <a href='tg://user?id={user.user_id}'>{user.fullname}</a> в {file.uploaded_at.strftime("%H:%M:%S %d.%m.%y")}
Размер файла: {round(file.file_size / (1024 * 1024), 2)} MB"""
            )
        files_info.append("")

    files_text = "\n".join(files_info)
    message_text = f"""<b>📜 История загрузок</b>
<i>Страница {page} из {total_pages}</i>

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
        file_log = next((l for l in logs if l.id == file_id), None)

        if not file_log:
            await callback.message.edit_text(
                """<b>📝 Подробно о файле</b>
        
Файл не найден ☹""",
                reply_markup=schedule_list_back_kb(),
            )
            return

        user = await stp_repo.user.get_user(user_id=file_log.uploaded_by_user_id)

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

        message_text = f"""<b>📝 Подробно о файле</b>

<b>📄 Название</b>
{file_log.file_name or "Unknown"}

<b>🤨 Загрузил</b>
{user_info}

<b>📅 Дата загрузки</b>
{file_log.uploaded_at.strftime("%d.%m.%Y в %H:%M:%S")}

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
            file_log = next((l for l in logs if l.id == file_id), None)

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
        log = next((l for l in logs if l.id == log_id), None)

        if not log:
            await callback.answer("Файл не найден", show_alert=True)
            return

        await callback.message.answer_document(document=log.file_id)
        await callback.answer("Файл отправлен!")
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}", show_alert=True)

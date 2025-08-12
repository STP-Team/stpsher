import os

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile

from infrastructure.database.repo.requests import RequestsRepo
from tgbot.filters.role import MipFilter
from tgbot.keyboards.mip.schedule.list import (
    schedule_list_kb,
    list_db_files_kb,
    schedule_list_back_kb,
    ScheduleListMenu,
    list_local_files_kb,
)
from tgbot.keyboards.mip.schedule.main import ScheduleMenu

mip_list_router = Router()
mip_list_router.message.filter(F.chat.type == "private", MipFilter())
mip_list_router.callback_query.filter(F.message.chat.type == "private", MipFilter())


@mip_list_router.callback_query(ScheduleMenu.filter(F.menu == "list"))
async def upload_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        """<b>📂 Просмотр файлов</b>
        
Здесь ты можешь посмотреть какие файлы сейчас находятся на сервере, а так же посмотреть историю изменений и выгрузить старые файлы""",
        reply_markup=schedule_list_kb(),
    )


@mip_list_router.callback_query(ScheduleListMenu.filter(F.menu == "local"))
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


@mip_list_router.callback_query(ScheduleListMenu.filter(F.menu == "history"))
async def show_history_files(callback: CallbackQuery, stp_repo: RequestsRepo):
    files_history = await stp_repo.upload.get_files_history()

    if not files_history:
        await callback.message.edit_text(
            """<b>📜 История загрузок</b>
        
История загрузок пуста :(""",
            reply_markup=schedule_list_back_kb(),
        )
        return

    files_info = []
    for file in files_history:
        user = await stp_repo.users.get_user(file.uploaded_by_user_id)

        files_info.append(
            f"""• <b>{file.file_name or "Unknown"}</b>
🤨 Загрузил: <a href='tg://user?id={user.user_id}'>{user.fullname}</a> в {file.uploaded_at.strftime("%H:%M:%S %d.%m.%y")}
🏋 Размер файла: {round(file.file_size / (1024 * 1024), 2)} MB"""
        )

    files_text = "\n\n".join(files_info)
    await callback.message.edit_text(
        f"<b>📜 История загрузок</b>\n\n{files_text}\n\n<i>Отображаются только 5 последних загрузок</i>",
        reply_markup=list_db_files_kb(schedule_files=files_history),
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


@mip_list_router.callback_query(F.data.startswith("download_db:"))
async def download_db_file(callback: CallbackQuery, stp_repo: RequestsRepo):
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

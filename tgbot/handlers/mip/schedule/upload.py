import asyncio
import logging
import os

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from tgbot.filters.role import MipFilter
from tgbot.keyboards.mip.schedule.main import ScheduleMenu, schedule_kb
from tgbot.misc.states.mip.upload import UploadFile

mip_upload_router = Router()
mip_upload_router.message.filter(F.chat.type == "private", MipFilter())
mip_upload_router.callback_query.filter(F.message.chat.type == "private", MipFilter())

logger = logging.getLogger(__name__)


@mip_upload_router.callback_query(ScheduleMenu.filter(F.menu == "upload"))
async def upload_menu(callback: CallbackQuery, state: FSMContext):
    bot_message = await callback.message.edit_text(
        """<b>📤 Загрузка</b>

Загрузи в этот чат файл для загрузки на сервер

<i>Если файл с таким же названием уже есть на сервере - он будет заменен твоим файлом</i>"""
    )
    await state.update_data(bot_message_id=bot_message.message_id)
    await state.set_state(UploadFile.file)


@mip_upload_router.message(F.document, UploadFile.file)
async def upload_file(message: Message, state: FSMContext):
    document = message.document
    file_id = document.file_id
    file_name = document.file_name
    file_size = document.file_size
    media_group_id = message.media_group_id

    await message.delete()

    # Сохранение файлов на диск
    file_path = f"uploads/{file_name}"
    file_replaced = os.path.exists(file_path)
    if file_replaced:
        os.remove(file_path)

    file = await message.bot.get_file(file_id)
    await message.bot.download_file(file.file_path, destination=file_path)

    # Сохраняем отправленные файлы в FSM
    while True:
        state_data = await state.get_data()
        uploaded_files = state_data.get("uploaded_files", [])

        # Дописываем инфо о загруженном файле
        file_info = {"name": file_name, "size": file_size, "replaced": file_replaced}
        uploaded_files.append(file_info)

        # Обновляем FSM с новым списком файлов и последним временем загрузки
        await state.update_data(
            uploaded_files=uploaded_files,
            last_media_group_id=media_group_id,
            last_upload_time=asyncio.get_event_loop().time(),
        )
        break

    # If media group, debounce finalize call
    if media_group_id:
        # To avoid multiple simultaneous tasks, cancel previous if any and schedule a new one
        # We'll keep track of the task in FSM or globally (simplified here)

        # Launch background checker (it will return quickly if called multiple times)
        asyncio.create_task(check_media_group_complete(message, state, media_group_id))
    else:
        # Single file upload: finalize immediately
        await finalize_upload(message, state)


async def check_media_group_complete(
    message: Message, state: FSMContext, media_group_id: str
):
    """
    Wait until no new files in the media group for 1 second, then finalize.
    Runs in background; multiple calls for the same media_group_id won't cause issues.
    """
    while True:
        await asyncio.sleep(0.5)
        state_data = await state.get_data()
        current_media_group_id = state_data.get("last_media_group_id")
        last_upload_time = state_data.get("last_upload_time", 0)

        # If media group changed or no more files, stop checking
        if current_media_group_id != media_group_id:
            return

        # If no new uploads in last 1 second, finalize
        if asyncio.get_event_loop().time() - last_upload_time > 1:
            await finalize_upload(message, state)
            return


async def finalize_upload(message: Message, state: FSMContext):
    state_data = await state.get_data()
    uploaded_files = state_data.get("uploaded_files", [])
    bot_message_id = state_data.get("bot_message_id")

    if not uploaded_files or bot_message_id is None:
        return

    files_count = len(uploaded_files)
    if files_count == 1:
        status_text = "<b>💾 Загружен 1 файл</b>\n\n"
    elif files_count in [2, 3, 4]:
        status_text = f"<b>💾 Загружено {files_count} файла</b>\n\n"
    else:
        status_text = f"<b>💾 Загружено {files_count} файлов</b>\n\n"

    for i, file_info in enumerate(uploaded_files, 1):
        size_mb = round(file_info["size"] / (1024 * 1024), 2)
        status_text += f"{i}. <b>{file_info['name']}</b> - {size_mb} МБ"
        if file_info["replaced"]:
            status_text += " <i>(заменён)</i>"
        status_text += "\n"

    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_message_id,
            text=status_text,
        )
    except Exception as e:
        logger.warning(f"Не удалось отредактировать сообщение: {e}")

    await state.clear()

    # Отправляем в меню графиков после загрузки файлов
    await message.answer(
        """📅 Меню графиков

Используй меню для выбора действия""",
        reply_markup=schedule_kb(),
    )

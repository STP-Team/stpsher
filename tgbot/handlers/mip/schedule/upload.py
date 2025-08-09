import os

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from tgbot.filters.role import MipFilter
from tgbot.keyboards.mip.schedule.main import ScheduleMenu
from tgbot.misc.states.mip.upload import UploadFile

mip_upload_router = Router()
mip_upload_router.message.filter(F.chat.type == "private", MipFilter())
mip_upload_router.callback_query.filter(F.message.chat.type == "private", MipFilter())


@mip_upload_router.callback_query(ScheduleMenu.filter(F.menu == "upload"))
async def upload_menu(callback: CallbackQuery, state: FSMContext):
    bot_message = await callback.message.edit_text("""<b>📤 Загрузка</b>
    
Загрузи этот чат файл для загрузки на сервер

<i>Если файл с таким же названием уже есть на сервере - он будет заменен твоим файлом</i>""")
    await state.update_data(bot_message_id=bot_message.message_id)
    await state.set_state(UploadFile.file)


@mip_upload_router.message(F.document)
async def upload_file(message: Message, state: FSMContext):
    document = message.document
    file_id = document.file_id
    file_name = document.file_name
    file_size = document.file_size

    state_data = await state.get_data()
    await message.delete()

    file = await message.bot.get_file(file_id)
    if os.path.exists(f"uploads/{file_name}"):
        os.remove(f"uploads/{file_name}")
    await message.bot.download_file(file.file_path, destination=f"uploads/{file_name}")

    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=state_data.get("bot_message_id"),
        text=f"""<b>💾 Загрузка документа</b>

Загружен документ <b>{file_name}</b>
Размер: {round(file_size / (1024 * 1024), 2)} МБ""",
    )

    await state.clear()

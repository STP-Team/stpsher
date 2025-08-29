import fnmatch
import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.orm import Session

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.filters.role import MipFilter
from tgbot.keyboards.mip.schedule.main import ScheduleMenu, schedule_kb
from tgbot.keyboards.mip.schedule.upload import schedule_upload_back_kb
from tgbot.misc.states.mip.upload import UploadFile
from tgbot.services.schedule.user_processor import (
    process_fired_users_with_stats,
    process_user_changes,
)

# Router setup
mip_upload_router = Router()
mip_upload_router.message.filter(F.chat.type == "private", MipFilter())
mip_upload_router.callback_query.filter(F.message.chat.type == "private", MipFilter())

logger = logging.getLogger(__name__)

# Constants
UPLOADS_DIR = Path("uploads")
SCHEDULE_PATTERNS = ["ГРАФИК * I*", "ГРАФИК * II*"]


@mip_upload_router.callback_query(ScheduleMenu.filter(F.menu == "upload"))
async def upload_menu(callback: CallbackQuery, state: FSMContext):
    """Display upload menu and wait for file."""
    bot_message = await callback.message.edit_text(
        """<b>📤 Загрузка файла</b>

Отправь файл для загрузки на сервер

<i>Если файл с таким же названием уже существует - он будет заменён</i>""",
        reply_markup=schedule_upload_back_kb(),
    )
    await state.update_data(bot_message_id=bot_message.message_id)
    await state.set_state(UploadFile.file)


@mip_upload_router.message(F.document)
async def upload_file(
    message: Message, state: FSMContext, stp_repo: MainRequestsRepo, main_db: Session
):
    """Handle single file upload and processing with change detection."""
    document = message.document
    await message.delete()

    try:
        # Step 1: Show initial processing status
        await _update_progress_status(
            message,
            state,
            "⏳ <b>Обработка файла...</b>\n\n"
            f"📄 <b>{document.file_name}</b>\n"
            f"Размер: {round(document.file_size / (1024 * 1024), 2)} МБ\n\n"
            "🔄 Загрузка файла на сервер...",
        )

        # Check if file with same name exists (for change detection)
        file_path = UPLOADS_DIR / document.file_name
        old_file_exists = file_path.exists()
        old_file_name = document.file_name if old_file_exists else None

        # Save old file temporarily for comparison if it exists
        temp_old_file = None
        if old_file_exists:
            temp_old_file = UPLOADS_DIR / f"temp_old_{document.file_name}"
            file_path.rename(temp_old_file)

        # Step 2: Update progress - downloading
        await _update_progress_status(
            message,
            state,
            "⏳ <b>Обработка файла...</b>\n\n"
            f"📄 <b>{document.file_name}</b>\n"
            f"Размер: {round(document.file_size / (1024 * 1024), 2)} МБ\n\n"
            "💾 Сохранение файла...",
        )

        # Download and save new file
        file_path = await _save_file(message, document)
        file_replaced = old_file_exists

        # Step 3: Update progress - logging to database
        await _update_progress_status(
            message,
            state,
            "⏳ <b>Обработка файла...</b>\n\n"
            f"📄 <b>{document.file_name}</b>\n"
            f"Размер: {round(document.file_size / (1024 * 1024), 2)} МБ\n\n"
            "📝 Логируем загрузку файла в базу данных...",
        )

        # Log file to database
        await stp_repo.upload.add_file_history(
            file_id=document.file_id,
            file_name=document.file_name,
            file_size=document.file_size,
            uploaded_by_user_id=message.from_user.id,
        )

        # Step 4: Update progress - processing file content
        await _update_progress_status(
            message,
            state,
            "⏳ <b>Обработка файла...</b>\n\n"
            f"📄 <b>{document.file_name}</b>\n"
            f"Размер: {round(document.file_size / (1024 * 1024), 2)} МБ\n\n"
            "🔍 Анализируем содержимого файла...",
        )

        # Process file and generate status
        status_text = _generate_file_status(document, file_replaced)
        user_stats = await _process_file(document.file_name, main_db)

        if user_stats:
            status_text += _generate_stats_text(user_stats)

        # Step 5: Check for schedule changes
        notified_users = []
        if old_file_exists and temp_old_file and _is_schedule_file(document.file_name):
            await _update_progress_status(
                message,
                state,
                "⏳ <b>Обработка файла...</b>\n\n"
                f"📄 <b>{document.file_name}</b>\n"
                f"Размер: {round(document.file_size / (1024 * 1024), 2)} МБ\n\n"
                "📊 Ищем изменений в расписании...",
            )

            from tgbot.services.schedule.change_detector import ScheduleChangeDetector

            change_detector = ScheduleChangeDetector()

            # Temporarily restore old file for comparison
            temp_old_file.rename(UPLOADS_DIR / f"old_{document.file_name}")

            try:
                await _update_progress_status(
                    message,
                    state,
                    "⏳ <b>Обработка файла...</b>\n\n"
                    f"📄 <b>{document.file_name}</b>\n"
                    f"Размер: {round(document.file_size / (1024 * 1024), 2)} МБ\n\n"
                    "📤 Проверяем изменения в графике и отправляем уведомления пользователям...",
                )

                notified_users = await change_detector.process_schedule_changes(
                    new_file_name=document.file_name,
                    old_file_name=f"old_{document.file_name}",
                    bot=message.bot,
                    stp_repo=stp_repo,
                )
            finally:
                # Clean up temporary old file
                old_file_path = UPLOADS_DIR / f"old_{document.file_name}"
                if old_file_path.exists():
                    old_file_path.unlink()

        # Add notification info to status
        if notified_users:
            status_text += "\n\n📤 <b>Изменения графика</b>\n"
            status_text += (
                f"Пользователей с измененным графиком: {len(notified_users)}\n"
            )
            status_text += "\n".join(
                f"• {name}" for name in notified_users[:5]
            )  # Show first 5
            if len(notified_users) > 5:
                status_text += f"\n... и еще {len(notified_users) - 5}"
        else:
            status_text += "\n\n📤 <b>Изменения графика</b>\n"
            status_text += (
                "Нет изменений в графике. Уведомления об изменении отправлены не будут"
            )

        # Step 6: Final status - completed
        await _update_status_message(message, state, status_text)

    except Exception as e:
        logger.error(f"File upload failed: {e}")
        await _show_error_message(message, state, "Ошибка при загрузке файла")
    finally:
        # Clean up any remaining temporary files
        for temp_file in UPLOADS_DIR.glob("temp_old_*"):
            temp_file.unlink()

        await state.clear()


async def _update_progress_status(
    message: Message, state: FSMContext, status_text: str
):
    """Update the bot message with current progress status."""
    state_data = await state.get_data()
    bot_message_id = state_data.get("bot_message_id")

    if bot_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=bot_message_id,
                text=status_text,
                reply_markup=None,  # Remove keyboard during processing
            )
        except Exception as e:
            logger.warning(f"Failed to update progress message: {e}")


def _is_schedule_file(file_name: str) -> bool:
    """Check if file is a schedule file based on patterns."""
    import fnmatch

    return any(fnmatch.fnmatch(file_name, pattern) for pattern in SCHEDULE_PATTERNS)


async def _save_file(message: Message, document) -> Path:
    """Download and save file to uploads directory."""
    UPLOADS_DIR.mkdir(exist_ok=True)
    file_path = UPLOADS_DIR / document.file_name

    # Remove existing file if present
    if file_path.exists():
        file_path.unlink()

    # Download file
    file = await message.bot.get_file(document.file_id)
    await message.bot.download_file(file.file_path, destination=str(file_path))

    return file_path


def _generate_file_status(document, file_replaced: bool) -> str:
    """Generate status message for uploaded file."""
    size_mb = round(document.file_size / (1024 * 1024), 2)
    status_text = "<b>✅ Файл успешно загружен</b>\n\n"
    status_text += f"📄 <b>{document.file_name}</b>\n"
    status_text += f"Размер: {size_mb} МБ\n"

    if file_replaced:
        status_text += "<i>Заменён существующий файл</i>"

    return status_text


async def _process_file(file_name: str, main_db: Session) -> dict | None:
    """Process file if it matches schedule patterns."""
    # Check if file matches schedule patterns
    if not any(fnmatch.fnmatch(file_name, pattern) for pattern in SCHEDULE_PATTERNS):
        return None

    try:
        file_path = UPLOADS_DIR / file_name

        # Process fired users
        fired_names = await process_fired_users_with_stats([file_path], main_db)

        # Process user changes
        updated_names, new_names = await process_user_changes(main_db, file_name)

        return {
            "fired_names": fired_names,
            "updated_names": updated_names,
            "new_names": new_names,
        }
    except Exception as e:
        logger.error(f"File processing failed: {e}")
        return None


def _generate_stats_text(stats: dict) -> str:
    """Generate statistics text from processing results."""
    text = "\n\n<b>📊 Статистика обработки</b>\n"

    sections = [
        ("🔥 Уволено", stats["fired_names"]),
        ("✏️ Обновлено", stats["updated_names"]),
        ("➕ Добавлено", stats["new_names"]),
    ]

    has_changes = False
    for title, names in sections:
        if names:
            has_changes = True
            text += f"\n{title} ({len(names)}):\n"
            text += "\n".join(f"• {name}" for name in names) + "\n"

    if not has_changes:
        text += "Уволенных, обновленных или добавленных пользователей нет"

    return text


async def _update_status_message(message: Message, state: FSMContext, status_text: str):
    """Update the bot message with upload status."""
    state_data = await state.get_data()
    bot_message_id = state_data.get("bot_message_id")

    if bot_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=bot_message_id,
                text=status_text,
                reply_markup=schedule_upload_back_kb(),  # Restore keyboard when done
            )
        except Exception as e:
            logger.warning(f"Failed to update message: {e}")


async def _show_error_message(message: Message, state: FSMContext, error_text: str):
    """Show error message to user."""
    state_data = await state.get_data()
    bot_message_id = state_data.get("bot_message_id")

    if bot_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=bot_message_id,
                text=f"❌ {error_text}",
                reply_markup=schedule_upload_back_kb(),
            )
        except Exception as e:
            logger.warning(f"Failed to show error: {e}")


async def _show_schedule_menu(message: Message):
    """Display the main schedule menu."""
    await message.answer(
        "<b>📅 Меню графиков</b>\n\nЗдесь ты найдешь все, что связано с графиками",
        reply_markup=schedule_kb(),
    )

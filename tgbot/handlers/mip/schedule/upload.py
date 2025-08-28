import fnmatch
import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.orm import Session

from infrastructure.database.repo.requests import RequestsRepo
from tgbot.filters.role import MipFilter
from tgbot.keyboards.mip.schedule.main import ScheduleMenu, schedule_kb
from tgbot.keyboards.mip.schedule.upload import schedule_upload_back_kb
from tgbot.misc.states.mip.upload import UploadFile
from tgbot.services.schedule.user_processor import (
    process_fired_users_with_stats,
    process_user_changes_with_stats,
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
    message: Message, state: FSMContext, stp_repo: RequestsRepo, stp_db: Session
):
    """Handle single file upload and processing with change detection."""
    document = message.document
    await message.delete()

    try:
        # Check if file with same name exists (for change detection)
        file_path = UPLOADS_DIR / document.file_name
        old_file_exists = file_path.exists()
        old_file_name = document.file_name if old_file_exists else None

        # Save old file temporarily for comparison if it exists
        temp_old_file = None
        if old_file_exists:
            temp_old_file = UPLOADS_DIR / f"temp_old_{document.file_name}"
            file_path.rename(temp_old_file)

        # Download and save new file
        file_path = await _save_file(message, document)
        file_replaced = old_file_exists

        # Log file to database
        await stp_repo.upload.add_file_history(
            file_id=document.file_id,
            file_name=document.file_name,
            file_size=document.file_size,
            uploaded_by_user_id=message.from_user.id,
        )

        # Process file and generate status
        status_text = _generate_file_status(document, file_replaced)
        user_stats = await _process_file(document.file_name, stp_db)

        if user_stats:
            status_text += _generate_stats_text(user_stats)

        # Check for schedule changes and send notifications
        notified_users = []
        if old_file_exists and temp_old_file and _is_schedule_file(document.file_name):
            from tgbot.services.schedule.change_detector import ScheduleChangeDetector

            change_detector = ScheduleChangeDetector()

            # Temporarily restore old file for comparison
            temp_old_file.rename(UPLOADS_DIR / f"old_{document.file_name}")

            try:
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
            status_text += "\n\n📤 <b>Отправлены уведомления</b>\n"
            status_text += f"Уведомлено специалистов: {len(notified_users)}\n"
            status_text += "\n".join(
                f"• {name}" for name in notified_users[:5]
            )  # Show first 5
            if len(notified_users) > 5:
                status_text += f"\n... и еще {len(notified_users) - 5}"

        # Update bot message with results
        await _update_status_message(message, state, status_text)

    except Exception as e:
        logger.error(f"File upload failed: {e}")
        await _show_error_message(message, state, "Ошибка при загрузке файла")
    finally:
        # Clean up any remaining temporary files
        for temp_file in UPLOADS_DIR.glob("temp_old_*"):
            temp_file.unlink()

        await state.clear()
        await _show_schedule_menu(message)


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
    status_text = "<b>💾 Файл загружен</b>\n\n"
    status_text += f"📄 <b>{document.file_name}</b>\n"
    status_text += f"Размер: {size_mb} МБ\n"

    if file_replaced:
        status_text += "<i>Заменён существующий файл</i>"

    return status_text


async def _process_file(file_name: str, stp_db: Session) -> dict | None:
    """Process file if it matches schedule patterns."""
    # Check if file matches schedule patterns
    if not any(fnmatch.fnmatch(file_name, pattern) for pattern in SCHEDULE_PATTERNS):
        return None

    try:
        file_path = UPLOADS_DIR / file_name

        # Process fired users
        fired_names = await process_fired_users_with_stats([file_path], stp_db)

        # Process user changes
        updated_names, new_names = await process_user_changes_with_stats(
            stp_db, file_name
        )

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
        text += "Изменений не обнаружено"

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
            )
        except Exception as e:
            logger.warning(f"Failed to show error: {e}")


async def _show_schedule_menu(message: Message):
    """Display the main schedule menu."""
    await message.answer(
        "<b>📅 Меню графиков</b>\n\nЗдесь ты найдешь все, что связано с графиками",
        reply_markup=schedule_kb(),
    )

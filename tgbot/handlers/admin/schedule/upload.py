import fnmatch
import logging
import re
from pathlib import Path

import pandas as pd
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.orm import Session
from stp_database import MainRequestsRepo

from tgbot.filters.role import AdministratorFilter
from tgbot.keyboards.admin.schedule.main import ScheduleMenu, schedule_kb
from tgbot.keyboards.admin.schedule.upload import schedule_upload_back_kb
from tgbot.misc.states.admin.upload import UploadFile
from tgbot.services.schedule.user_processor import (
    process_fired_users_with_stats,
    process_user_changes,
)

# Router setup
admin_upload_router = Router()
admin_upload_router.message.filter(F.chat.type == "private", AdministratorFilter())
admin_upload_router.callback_query.filter(
    F.message.chat.type == "private", AdministratorFilter()
)

logger = logging.getLogger(__name__)

# Constants
UPLOADS_DIR = Path("uploads")
SCHEDULE_PATTERNS = ["ГРАФИК * I*", "ГРАФИК * II*"]
DUTIES_PATTERNS = ["Старшинство НТП*", "*Старшинство НТП*", "*старшинство*", "*НТП*"]
STUDIES_PATTERNS = ["Обучения *", "*обучения*", "*обучение*", "*Обучение*"]


@admin_upload_router.callback_query(ScheduleMenu.filter(F.menu == "upload"))
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


@admin_upload_router.message(F.document)
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
        await _save_file(message, document)
        file_replaced = old_file_exists

        # Step 3: Update progress - logging to database
        await _update_progress_status(
            message,
            state,
            "⏳ <b>Обработка файла...</b>\n\n"
            f"📄 <b>{document.file_name}</b>\n"
            f"Размер: {round(document.file_size / (1024 * 1024), 2)} МБ\n"
            f"Тип: {_get_file_type_display(document.file_name)}\n"
            f"Статус: {'🔄 Заменит существующий' if old_file_exists else '✨ Новый файл'}\n\n"
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
            "🔍 Анализируем содержимое файла...",
        )

        # Get detailed file statistics
        file_stats = await _get_detailed_file_stats(
            document.file_name, old_file_exists, temp_old_file
        )

        # Process file and generate status
        status_text = _generate_file_status(document, file_replaced)

        # Check if this is a studies file for different processing
        studies_stats = await _process_studies_file(document.file_name)
        if studies_stats:
            # For studies files, only show studies stats (no detailed file stats)
            status_text += _generate_studies_stats_text(studies_stats)

            # Step 5a: Check for upcoming studies and send notifications
            await _update_progress_status(
                message,
                state,
                "⏳ <b>Обработка файла...</b>\n\n"
                f"📄 <b>{document.file_name}</b>\n"
                f"Размер: {round(document.file_size / (1024 * 1024), 2)} МБ\n"
                f"Тип: {_get_file_type_display(document.file_name)}\n\n"
                "📤 Проверяем предстоящие обучения и отправляем уведомления...",
            )

            # Check for upcoming studies and notify participants
            from tgbot.services.schedulers.studies import check_upcoming_studies

            notification_results = await check_upcoming_studies(main_db, message.bot)

            # Add notification results to status
            if notification_results.get("status") == "success":
                sessions_count = notification_results.get("sessions", 0)
                notifications_count = notification_results.get("notifications", 0)

                if sessions_count > 0:
                    status_text += "\n\n📤 <b>Уведомления об обучениях</b>\n"
                    status_text += f"• Найдено предстоящих обучений (в течение недели): {sessions_count}\n"
                    status_text += (
                        f"• Отправлено уведомлений участникам: {notifications_count}"
                    )
                else:
                    status_text += "\n\n📤 <b>Уведомления об обучениях</b>\n"
                    status_text += "• Предстоящих обучений в течение недели не найдено"
            else:
                error_msg = notification_results.get("message", "Неизвестная ошибка")
                status_text += "\n\n📤 <b>Уведомления об обучениях</b>\n"
                status_text += f"⚠️ Ошибка проверки уведомлений: {error_msg}"
        else:
            # For non-studies files, show detailed stats and user processing
            status_text += _generate_detailed_file_stats_text(file_stats)

            user_stats = await _process_file(document.file_name, main_db)
            if user_stats:
                status_text += _generate_stats_text(user_stats)

        # Step 5: Check for schedule changes
        changed_users = []
        notified_users = []
        if old_file_exists and temp_old_file and _is_schedule_file(document.file_name):
            # Include file stats in the progress message
            stats_text = _generate_detailed_file_stats_text(file_stats)
            await _update_progress_status(
                message,
                state,
                "⏳ <b>Обработка файла...</b>\n\n"
                f"📄 <b>{document.file_name}</b>\n"
                f"Размер: {round(document.file_size / (1024 * 1024), 2)} МБ"
                + stats_text
                + "\n\n📊 Ищем изменений в расписании...",
            )

            from tgbot.services.schedule.change_detector import ScheduleChangeDetector

            change_detector = ScheduleChangeDetector()

            # Temporarily restore old file for comparison
            temp_old_file.rename(UPLOADS_DIR / f"old_{document.file_name}")

            try:
                stats_text = _generate_detailed_file_stats_text(file_stats)
                await _update_progress_status(
                    message,
                    state,
                    "⏳ <b>Обработка файла...</b>\n\n"
                    f"📄 <b>{document.file_name}</b>\n"
                    f"Размер: {round(document.file_size / (1024 * 1024), 2)} МБ"
                    + stats_text
                    + "\n\n📤 Проверяем изменения в графике и отправляем уведомления пользователям...",
                )

                (
                    changed_users,
                    notified_users,
                ) = await change_detector.process_schedule_changes(
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

        # Add notification info to status (only for schedule files)
        if _is_schedule_file(document.file_name):
            if changed_users:
                status_text += "\n\n📤 <b>Изменения графика</b>\n"
                status_text += (
                    f"Пользователей с измененным графиком: {len(changed_users)}\n"
                )
                # Extract just the names from the change data
                user_names = []
                for user_change in changed_users:
                    if isinstance(user_change, dict) and "fullname" in user_change:
                        user_names.append(user_change["fullname"])
                    elif isinstance(user_change, str):
                        user_names.append(user_change)
                    else:
                        user_names.append(str(user_change))

                status_text += "\n".join(
                    f"• {name}" for name in user_names[:5]
                )  # Show first 5
                if len(user_names) > 5:
                    status_text += f"\n... и еще {len(user_names) - 5}"

                status_text += (
                    f"\n\nВсего удалось отправить {len(notified_users)} уведомлений"
                )
            else:
                status_text += "\n\n📤 <b>Изменения графика</b>\n"
                status_text += "Нет изменений в графике. Уведомления об изменении отправлены не будут"

        # Step 6: Final status - completed
        await _update_status_message(message, state, status_text)

    except Exception as e:
        logger.error(f"File upload failed: {e}")
        await _show_error_message(message, state, "Ошибка при загрузке файла")
    finally:
        # Clean up any remaining temporary files
        for temp_file in UPLOADS_DIR.glob("temp_old_*"):
            temp_file.unlink()

        # Clean up old temp_current_ files if a newer version exists
        await _cleanup_old_temp_files(document.file_name)

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


def _is_studies_file(file_name: str) -> bool:
    """Check if file is a studies file based on patterns."""
    import fnmatch

    return any(fnmatch.fnmatch(file_name, pattern) for pattern in STUDIES_PATTERNS)


def _is_duties_file(file_name: str) -> bool:
    """Check if file is a duties file based on patterns."""
    import fnmatch

    return any(fnmatch.fnmatch(file_name, pattern) for pattern in DUTIES_PATTERNS)


def _get_file_type_display(file_name: str) -> str:
    """Get file type display text based on file name patterns."""
    if _is_schedule_file(file_name):
        return "📅 График"
    elif _is_duties_file(file_name):
        return "⚔️ Старшинство НТП"
    elif _is_studies_file(file_name):
        return "📚 Обучения"
    else:
        return "📄 Обычный файл"


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
                reply_markup=schedule_upload_back_kb(upload_done=True),
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


async def _get_detailed_file_stats(
    file_name: str, old_file_exists: bool, temp_old_file: Path = None
) -> dict:
    """Get detailed statistics for both new and old files."""
    stats = {
        "new_file": {"total_people": 0, "schedule_people": 0, "fired_people": 0},
        "old_file": {"total_people": 0, "schedule_people": 0, "fired_people": 0}
        if old_file_exists
        else None,
    }

    try:
        # Get stats for new file
        new_file_path = UPLOADS_DIR / file_name
        if new_file_path.exists():
            stats["new_file"] = _extract_file_stats(new_file_path)

        # Get stats for old file if it exists
        if old_file_exists and temp_old_file and temp_old_file.exists():
            stats["old_file"] = _extract_file_stats(temp_old_file)

    except Exception as e:
        logger.error(f"Error getting detailed file stats: {e}")

    return stats


def _extract_file_stats(file_path: Path) -> dict:
    """Extract statistics from a single Excel file."""
    stats = {"total_people": 0, "schedule_people": 0, "fired_people": 0}

    try:
        # For temporary files, check against original name pattern
        original_name = file_path.name
        if file_path.name.startswith("temp_old_"):
            original_name = file_path.name.replace("temp_old_", "")

        if not _is_schedule_file(original_name):
            return stats

        # Read Excel file directly from path
        df = pd.read_excel(file_path, sheet_name=0, header=None, dtype=str)

        # Extract users directly from dataframe using the same logic as user_processor
        stats["total_people"] = _count_users_in_dataframe(df)

        # Count people with actual schedule data (not just in list)
        stats["schedule_people"] = _count_users_with_schedule(df)

        # Count fired people - for temp files, we need to temporarily create a file in uploads
        if file_path.name.startswith("temp_old_"):
            # For old files, we can't easily extract fired users without the proper file structure
            # So we'll skip this for now and just show 0
            stats["fired_people"] = 0
        else:
            from tgbot.services.scheduler import get_fired_users_from_excel

            fired_users = get_fired_users_from_excel([str(file_path)])
            stats["fired_people"] = len(fired_users)

    except Exception as e:
        logger.error(f"Error extracting stats from {file_path}: {e}")

    return stats


def _count_users_in_dataframe(df: pd.DataFrame) -> int:
    """Count users in dataframe using same logic as user_processor."""
    users_found = set()

    # Find header row and columns using same logic as user_processor
    header_info = _find_header_columns_direct(df)
    if not header_info:
        return 0

    # Extract users from the dataframe
    for row_idx in range(header_info["header_row"] + 1, len(df)):
        fullname_cell = (
            str(df.iloc[row_idx, header_info["fullname_col"]])
            if pd.notna(df.iloc[row_idx, header_info["fullname_col"]])
            else ""
        )

        if _is_valid_fullname_direct(fullname_cell):
            users_found.add(fullname_cell.strip())

    return len(users_found)


def _count_users_with_schedule(df: pd.DataFrame) -> int:
    """Count users who have actual schedule data in their rows."""
    schedule_count = 0

    for row_idx in range(len(df)):
        for col_idx in range(min(4, len(df.columns))):
            cell_value = (
                str(df.iloc[row_idx, col_idx])
                if pd.notna(df.iloc[row_idx, col_idx])
                else ""
            )
            if _is_valid_person_name(cell_value.strip()):
                # Check if person has schedule data in the row
                has_schedule = False
                for schedule_col in range(4, min(len(df.columns), 50)):
                    if schedule_col < len(df.columns):
                        schedule_val = (
                            str(df.iloc[row_idx, schedule_col])
                            if pd.notna(df.iloc[row_idx, schedule_col])
                            else ""
                        )
                        if schedule_val.strip() and schedule_val.strip() not in [
                            "",
                            "nan",
                            "None",
                        ]:
                            has_schedule = True
                            break
                if has_schedule:
                    schedule_count += 1
                break

    return schedule_count


def _find_header_columns_direct(df: pd.DataFrame) -> dict:
    """Find header row and column positions directly from dataframe."""
    for row_idx in range(min(10, len(df))):
        row_values = []
        for col_idx in range(min(10, len(df.columns))):
            cell_value = (
                str(df.iloc[row_idx, col_idx])
                if pd.notna(df.iloc[row_idx, col_idx])
                else ""
            )
            row_values.append(cell_value.strip().upper())

        position_col = head_col = None

        for col_idx, value in enumerate(row_values):
            if "ДОЛЖНОСТЬ" in value:
                position_col = col_idx
            if "РУКОВОДИТЕЛЬ" in value:
                head_col = col_idx

        if position_col is not None and head_col is not None:
            return {
                "header_row": row_idx,
                "fullname_col": 0,
                "position_col": position_col,
                "head_col": head_col,
            }

    return None


def _is_valid_fullname_direct(fullname_cell: str) -> bool:
    """Check if cell contains valid fullname using same logic as user_processor."""
    return (
        len(fullname_cell.split()) >= 3
        and re.search(r"[А-Яа-я]", fullname_cell)
        and not re.search(r"\d", fullname_cell)
        and fullname_cell.strip() not in ["", "nan", "None"]
        and "переводы" not in fullname_cell.lower()
        and "увольнения" not in fullname_cell.lower()
    )


def _is_valid_person_name(text: str) -> bool:
    """Check if text is a valid person name."""
    if not text or text.strip() in ["", "nan", "None", "ДАТА →"]:
        return False

    text = text.strip()
    words = text.split()

    # Should have at least 2 words (surname + name)
    if len(words) < 2:
        return False

    # Should contain Cyrillic characters
    if not re.search(r"[А-Яа-я]", text):
        return False

    # Should not contain digits
    if re.search(r"\d", text):
        return False

    # Skip service records
    if text.upper() in ["СТАЖЕРЫ ОБЩЕГО РЯДА", "ДАТА", "ПЕРЕВОДЫ/УВОЛЬНЕНИЯ"]:
        return False

    return True


def _generate_detailed_file_stats_text(stats: dict) -> str:
    """Generate detailed statistics text for both files."""
    if not stats:
        return ""

    text = "\n\n📊 <b>Детальная статистика</b>\n"

    # New file stats
    new_stats = stats.get("new_file", {})
    text += "\n<blockquote expandable>📄 <b>Новый файл:</b>\n"
    text += f"• Всего сотрудников: {new_stats.get('total_people', 0)}\n"
    text += f"• С графиком: {new_stats.get('schedule_people', 0)}\n"
    if new_stats.get("fired_people", 0) > 0:
        text += f"• К увольнению: {new_stats.get('fired_people', 0)}\n"

    # Old file stats (if exists)
    old_stats = stats.get("old_file")
    if old_stats:
        text += "\n📋 <b>Предыдущий файл:</b>\n"
        text += f"• Всего сотрудников: {old_stats.get('total_people', 0)}\n"
        text += f"• С графиком: {old_stats.get('schedule_people', 0)}\n"
        if old_stats.get("fired_people", 0) > 0:
            text += f"• К увольнению: {old_stats.get('fired_people', 0)}\n"

        # Show differences
        total_diff = new_stats.get("total_people", 0) - old_stats.get("total_people", 0)
        schedule_diff = new_stats.get("schedule_people", 0) - old_stats.get(
            "schedule_people", 0
        )

        if total_diff != 0 or schedule_diff != 0:
            text += "\n📈 <b>Изменения:</b>\n"
            if total_diff > 0:
                text += f"• +{total_diff} сотрудников\n"
            elif total_diff < 0:
                text += f"• {total_diff} сотрудников\n"

            if schedule_diff > 0:
                text += f"• +{schedule_diff} с графиком\n"
            elif schedule_diff < 0:
                text += f"• {schedule_diff} с графиком\n"

    return text + "</blockquote>"


async def _process_studies_file(file_name: str) -> dict | None:
    """Process studies file if it matches studies patterns."""
    # Check if file matches studies patterns
    if not _is_studies_file(file_name):
        return None

    try:
        from tgbot.services.schedule.studies_parser import StudiesScheduleParser

        file_path = UPLOADS_DIR / file_name
        parser = StudiesScheduleParser()
        sessions = parser.parse_studies_file(file_path)

        # Calculate statistics
        total_sessions = len(sessions)
        total_participants = 0
        unique_participants = set()
        present_participants = 0

        for session in sessions:
            total_participants += len(session.participants)
            for area, name, rg, attendance, reason in session.participants:
                unique_participants.add(name)
                if attendance == "+":
                    present_participants += 1

        return {
            "total_sessions": total_sessions,
            "total_participants": total_participants,
            "unique_participants": len(unique_participants),
            "present_participants": present_participants,
        }
    except Exception as e:
        logger.error(f"Studies file processing failed: {e}")
        return None


def _generate_studies_stats_text(stats: dict) -> str:
    """Generate statistics text from studies processing results."""
    text = "\n\n<b>📚 Статистика обучений</b>\n"

    total_sessions = stats.get("total_sessions", 0)
    stats.get("total_participants", 0)
    unique_participants = stats.get("unique_participants", 0)

    text += f"• Всего обучений в файле: {total_sessions}\n"
    text += f"• Всего участников записано: {unique_participants}"

    return text


async def _cleanup_old_temp_files(new_filename: str):
    """Clean up old temp_current_ files when a new version is uploaded."""
    try:
        # Check if there's an old temp_current_ file with the same base name
        temp_current_file = UPLOADS_DIR / f"temp_current_{new_filename}"
        if temp_current_file.exists():
            temp_current_file.unlink()
            logger.info(
                f"Cleaned up old temp_current_ file: temp_current_{new_filename}"
            )
    except Exception as e:
        logger.warning(f"Failed to cleanup old temp file: {e}")


async def _show_schedule_menu(message: Message):
    """Display the main schedule menu."""
    await message.answer(
        "<b>📅 Меню графиков</b>\n\nЗдесь ты найдешь все, что связано с графиками",
        reply_markup=schedule_kb(),
    )

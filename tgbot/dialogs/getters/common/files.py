"""Геттеры, связанные с файлами."""

from datetime import datetime
from pathlib import Path

from aiogram_dialog import DialogManager
from stp_database import MainRequestsRepo

from tgbot.misc.helpers import format_fullname, strftime_date
from tgbot.services.files_processing.utils.files import (
    FileTypeDetector,
    generate_detailed_stats_text,
    generate_studies_stats_text,
    generate_user_changes_text,
)


async def get_local_files(**kwargs) -> dict:
    """Получает список файлов из папки /uploads."""
    uploads_dir = Path("uploads")

    if not uploads_dir.exists():
        return {"files": []}

    files = []
    for idx, file_path in enumerate(uploads_dir.iterdir(), start=1):
        if file_path.is_file():
            file_stat = file_path.stat()
            modified_date = datetime.fromtimestamp(file_stat.st_mtime).strftime(
                strftime_date
            )
            files.append((
                file_path.name,  # item[0] - имя файла
                f"{file_stat.st_size / 1024:.2f} KB",  # item[1] - размер
                file_path.suffix or "Неизвестно",  # item[2] - тип
                modified_date,  # item[3] - дата изменения
            ))

    return {"files": files}


async def get_local_file_details(
    stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> dict:
    """Получает детальную информацию о файле из локальной папки и БД."""
    file_name = dialog_manager.dialog_data.get("selected_file")

    if not file_name:
        return {"file_info": None}

    # Получаем локальную информацию о файле
    file_path = Path("uploads") / file_name
    if not file_path.exists():
        return {"file_info": None}

    file_stat = file_path.stat()
    from datetime import datetime

    modified_date = datetime.fromtimestamp(file_stat.st_mtime)

    # Получаем информацию из БД
    db_records = await stp_repo.upload.get_files(file_name=file_name)

    file_info = {
        "name": file_name,
        "size": f"{file_stat.st_size / 1024:.2f} KB",
        "type": file_path.suffix or "Неизвестно",
        "modified": modified_date.strftime(strftime_date),
        "db_count": len(db_records) if db_records else 0,
    }

    db_record = False
    # Если есть записи в БД, берем последнюю
    if db_records:
        db_record = True
        latest = db_records[0]
        file_info["uploaded_by"] = latest.uploaded_by_user_id
        uploaded_by_user = await stp_repo.employee.get_users(
            user_id=latest.uploaded_by_user_id
        )
        uploaded_by_text = format_fullname(uploaded_by_user, True, True)
        file_info["uploaded_by_fullname"] = uploaded_by_text
        file_info["uploaded_at"] = latest.uploaded_at.strftime(strftime_date)

    return {
        "file_info": file_info,
        "db_record": db_record,
    }


async def get_file_history(
    stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> dict:
    """Получает историю файлов с таким же именем из БД."""
    file_name = dialog_manager.dialog_data.get("selected_file")

    if not file_name:
        return {"history": []}

    db_records = await stp_repo.upload.get_files(file_name=file_name)

    # Собираем все user_id и получаем пользователей одним запросом
    user_ids = [record.uploaded_by_user_id for record in db_records]
    users_list = await stp_repo.employee.get_users(user_id=user_ids)

    # Преобразуем список в словарь для быстрого доступа
    users_map = {user.user_id: user for user in users_list}

    history = []
    for record in db_records:
        uploaded_by_user = users_map.get(record.uploaded_by_user_id)
        fullname = format_fullname(
            uploaded_by_user,
            True,
            True,
        )

        history.append((
            record.id,  # item[0] - database record id (для item_id)
            record.file_name or file_name,  # item[1] - имя файла
            f"{record.file_size / 1024:.2f} KB"
            if record.file_size
            else "Н/Д",  # item[2] - размер
            record.uploaded_at.strftime(strftime_date),  # item[3] - дата загрузки
            record.uploaded_by_user_id,  # item[4] - кто загрузил
            record.file_id,  # item[5] - Telegram file_id
            fullname,  # item[6]
        ))

    # Сохраняем историю в dialog_data для доступа в event handler
    dialog_manager.dialog_data["history"] = history

    return {"history": history}


async def get_all_files_history(stp_repo: MainRequestsRepo, **_kwargs) -> dict:
    """Получает список всех загруженных файлов из БД."""
    db_records = await stp_repo.upload.get_files()

    # Собираем все user_id и получаем пользователей одним запросом
    user_ids = [record.uploaded_by_user_id for record in db_records]
    users_list = await stp_repo.employee.get_users(user_id=user_ids)

    # Преобразуем список в словарь для быстрого доступа
    users_map = {user.user_id: user for user in users_list}

    files = []
    for record in db_records:
        uploaded_by_user = users_map.get(record.uploaded_by_user_id)
        uploaded_by_text = format_fullname(
            uploaded_by_user,
            True,
            True,
        )

        files.append((
            record.id,  # item[0] - database record id (для item_id)
            record.file_name,  # item[1] - имя файла
            f"{record.file_size / 1024:.2f} KB"
            if record.file_size
            else "Н/Д",  # item[2] - размер
            record.uploaded_at.strftime(strftime_date),  # item[3] - дата загрузки
            record.uploaded_by_user_id,  # item[4] - кто загрузил
            record.file_id,  # item[5] - Telegram file_id
            uploaded_by_text,  # item[6] - имя пользователя
        ))

    return {"files": files}


async def get_history_file_details(
    stp_repo: MainRequestsRepo, dialog_manager: DialogManager, **_kwargs
) -> dict:
    """Получает детальную информацию о файле из истории загрузок."""
    history_file_id = dialog_manager.dialog_data.get("selected_history_file")

    if not history_file_id:
        return {"file_info": None}

    # Получаем информацию о файле из БД
    record = await stp_repo.upload.get_file_by_id(main_id=history_file_id)
    if not record:
        return {"file_info": None}

    uploaded_user = await stp_repo.employee.get_users(
        user_id=record.uploaded_by_user_id
    )
    uploaded_by_text = format_fullname(
        uploaded_user,
        True,
        True,
    )

    file_info = {
        "id": record.id,
        "name": record.file_name,
        "size": f"{record.file_size / 1024:.2f} KB" if record.file_size else "Н/Д",
        "uploaded_at": record.uploaded_at.strftime(strftime_date),
        "uploaded_by_fullname": uploaded_by_text,
        "file_id": record.file_id,
    }

    return {"file_info": file_info}


async def get_upload_status(dialog_manager: DialogManager, **_kwargs) -> dict:
    """Получает статус текущей загрузки файла с результатами обработки.

    Args:
        dialog_manager: Менеджер диалога

    Returns:
        Словарь с информацией о загрузке и обработке
    """
    data = dialog_manager.dialog_data

    file_name = data.get("upload_file_name", "Неизвестно")
    file_size = data.get("upload_file_size", 0)
    mime_type = data.get("upload_mime_type", "unknown")
    file_type = data.get("upload_file_type", "📄 Обычный файл")
    upload_error = data.get("upload_error")
    upload_time = data.get("upload_time", 0)
    actual_size = data.get("upload_actual_size", file_size)
    file_replaced = data.get("upload_file_replaced", False)
    processing_results = data.get("processing_results", {})

    upload_progress_text = data.get("upload_progress_text", "Подготовка...")

    # Форматируем размер
    if file_size:
        size_kb = file_size / 1024
        size_mb = size_kb / 1024
        if size_mb >= 1:
            size_str = f"{size_mb:.2f} MB"
        else:
            size_str = f"{size_kb:.2f} KB"
    else:
        size_str = "Неизвестно"

    # Формируем текст обработки
    processing_text = ""

    # Для файлов расписания
    if FileTypeDetector.is_schedule_file(file_name):
        new_stats = processing_results.get("new_stats")
        old_stats = processing_results.get("old_stats")

        if new_stats:
            processing_text += generate_detailed_stats_text(new_stats, old_stats)

        # Добавляем информацию об изменениях пользователей
        fired = processing_results.get("fired_names", [])
        updated = processing_results.get("updated_names", [])
        new = processing_results.get("new_names", [])

        if fired or updated or new:
            processing_text += generate_user_changes_text(fired, updated, new)

        # Добавляем информацию об изменениях в расписании
        changed_users = processing_results.get("changed_users", [])
        notified_users = processing_results.get("notified_users", [])

        if changed_users:
            processing_text += "<b>📤 Изменения графика</b>"
            processing_text += "\n<blockquote expandable>"

            # Показываем всех пользователей со статусом уведомления
            for user_info in changed_users:
                if isinstance(user_info, dict):
                    name = user_info.get("name", "Неизвестно")
                    status = user_info.get("status", "❌")
                    processing_text += f"\n{name}: {status}"
                else:
                    # Обратная совместимость: если это строка
                    processing_text += f"\n• {user_info}"

            processing_text += (
                f"\n\n✅ <b>Отправлено уведомлений:</b> "
                f"{len(notified_users)}</blockquote>"
            )
        elif file_replaced:
            processing_text += "\n📤 <b>Изменения графика</b>\n"
            processing_text += "Изменений в графике не обнаружено"

    # Для файлов обучений
    elif FileTypeDetector.is_studies_file(file_name):
        studies_stats = processing_results.get("studies_stats")
        if studies_stats:
            processing_text += generate_studies_stats_text(studies_stats)

            # Добавляем информацию об уведомлениях
            notification_results = processing_results.get("notification_results", {})
            if notification_results.get("status") == "success":
                sessions = notification_results.get("sessions", 0)
                notifications = notification_results.get("notifications", 0)

                processing_text += "\n📤 <b>Уведомления об обучениях</b>\n"
                if sessions > 0:
                    processing_text += (
                        f"• Предстоящих обучений (в течение недели): {sessions}\n"
                    )
                    processing_text += f"• Отправлено уведомлений: {notifications}"
                else:
                    processing_text += (
                        "• Предстоящих обучений в течение недели не найдено"
                    )
            elif "message" in notification_results:
                processing_text += "\n📤 <b>Уведомления об обучениях</b>\n"
                processing_text += f"⚠️ Ошибка: {notification_results.get('message')}"

    processing_complete = data.get("processing_complete", False)

    return {
        "file_name": file_name,
        "file_size": size_str,
        "file_type": file_type,
        "file_size_bytes": file_size,
        "actual_size_bytes": actual_size,
        "mime_type": mime_type,
        "upload_error": upload_error,
        "upload_time": f"{upload_time:.2f}" if upload_time else "—",
        "file_replaced": file_replaced,
        "processing_text": processing_text,
        "has_error": bool(upload_error),
        "has_processing": bool(processing_text),
        "upload_progress_text": upload_progress_text,
        "processing_complete": processing_complete,
    }

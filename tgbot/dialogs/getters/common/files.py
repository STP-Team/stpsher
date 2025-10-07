"""5BB5@K 4;O 480;>30 D09;>2."""

from pathlib import Path

from aiogram_dialog import DialogManager

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.dialogs.getters.common.search import short_name


async def get_local_files(**kwargs) -> dict:
    """Получает список файлов из папки /uploads."""
    from datetime import datetime

    uploads_dir = Path("uploads")

    if not uploads_dir.exists():
        return {"files": []}

    files = []
    for idx, file_path in enumerate(uploads_dir.iterdir(), start=1):
        if file_path.is_file():
            file_stat = file_path.stat()
            modified_date = datetime.fromtimestamp(file_stat.st_mtime).strftime(
                "%d.%m.%Y %H:%M"
            )
            files.append(
                (
                    file_path.name,  # item[0] - имя файла
                    f"{file_stat.st_size / 1024:.2f} KB",  # item[1] - размер
                    file_path.suffix or "Неизвестно",  # item[2] - тип
                    modified_date,  # item[3] - дата изменения
                )
            )

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
    db_records = await stp_repo.upload.get_files_history(file_name=file_name)

    file_info = {
        "name": file_name,
        "size": f"{file_stat.st_size / 1024:.2f} KB",
        "type": file_path.suffix or "Неизвестно",
        "modified": modified_date.strftime("%d.%m.%Y %H:%M"),
        "db_count": len(db_records) if db_records else 0,
    }

    db_record = False
    # Если есть записи в БД, берем последнюю
    if db_records:
        db_record = True
        latest = db_records[0]
        file_info["uploaded_by"] = latest.uploaded_by_user_id
        uploaded_by_user = await stp_repo.employee.get_user(
            user_id=latest.uploaded_by_user_id
        )
        print(uploaded_by_user)
        file_info["uploaded_by_fullname"] = uploaded_by_user.fullname
        file_info["uploaded_at"] = latest.uploaded_at.strftime("%d.%m.%Y %H:%M")

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

    db_records = await stp_repo.upload.get_files_history(file_name=file_name)

    history = []
    for record in db_records:
        uploaded_by_user = await stp_repo.employee.get_user(
            user_id=record.uploaded_by_user_id
        )
        history.append(
            (
                record.id,  # item[0] - database record id (для item_id)
                record.file_name or file_name,  # item[1] - имя файла
                f"{record.file_size / 1024:.2f} KB"
                if record.file_size
                else "Н/Д",  # item[2] - размер
                record.uploaded_at.strftime(
                    "%d.%m.%Y %H:%M"
                ),  # item[3] - дата загрузки
                record.uploaded_by_user_id,  # item[4] - кто загрузил
                record.file_id,  # item[5] - Telegram file_id
                short_name(uploaded_by_user.fullname),  # item[6]
            )
        )

    # Сохраняем историю в dialog_data для доступа в event handler
    dialog_manager.dialog_data["history"] = history

    return {"history": history}

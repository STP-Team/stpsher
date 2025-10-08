"""Upload handlers for file upload dialog."""

import asyncio
import logging
from pathlib import Path

from aiogram import Bot
from aiogram.types import CallbackQuery, Document, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button
from sqlalchemy.orm import Session

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.dialogs.states.common.files import Files
from tgbot.services.schedule.file_processor import (
    FileProcessor,
    FileStatsExtractor,
    FileTypeDetector,
)

logger = logging.getLogger(__name__)


async def on_document_uploaded(
    message: Message,
    _widget: MessageInput,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик загрузки документа пользователем с полной обработкой файла.

    Args:
        message: Сообщение с документом от пользователя
        _widget: MessageInput виджет
        dialog_manager: Менеджер диалога
    """
    # Удаляем сообщение пользователя с документом
    try:
        await message.delete()
    except Exception:
        pass  # Игнорируем ошибки удаления

    if not message.document:
        await message.answer("❌ Пожалуйста, отправь файл как документ")
        return

    document: Document = message.document
    bot: Bot = dialog_manager.middleware_data.get("bot")
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data.get("stp_repo")
    main_db: Session = dialog_manager.middleware_data.get("main_db")

    if not bot or not stp_repo:
        await message.answer("❌ Ошибка инициализации")
        return

    # Валидация размера файла (макс 20MB)
    max_size = 20 * 1024 * 1024  # 20MB
    if document.file_size and document.file_size > max_size:
        dialog_manager.dialog_data["upload_error"] = (
            f"Файл слишком большой: {document.file_size / 1024 / 1024:.2f} MB. "
            f"Максимальный размер: 20 MB"
        )
        await dialog_manager.switch_to(Files.upload_error)
        return

    # Определяем тип файла
    file_name = document.file_name or f"file_{document.file_id[:8]}"
    file_type = FileTypeDetector.get_file_type_display(file_name)

    # Определяем количество шагов для прогресса заранее
    total_steps = 3  # Базовые: скачивание, сохранение в БД, завершение
    is_schedule = FileTypeDetector.is_schedule_file(file_name)
    is_studies = FileTypeDetector.is_studies_file(file_name)

    if is_schedule:
        total_steps += 2  # статистика + обработка пользователей
        if main_db:
            total_steps += 1  # проверка изменений расписания
    elif is_studies:
        total_steps += 1  # обработка обучений
        if main_db:
            total_steps += 1  # уведомления

    # Сохраняем информацию о файле
    dialog_manager.dialog_data.update({
        "upload_file_id": document.file_id,
        "upload_file_name": file_name,
        "upload_file_size": document.file_size,
        "upload_mime_type": document.mime_type,
        "upload_file_type": file_type,
        "upload_start_time": asyncio.get_event_loop().time(),
        "upload_progress": 0,
        "upload_progress_text": "Подготовка...",
        "upload_total_steps": total_steps,
        "processing_complete": False,
    })

    # Переключаемся на экран обработки
    await dialog_manager.switch_to(Files.upload_processing)

    # Даём время на отображение окна обработки
    await asyncio.sleep(0.5)

    async def update_progress(step: int, total: int, text: str):
        """Обновляет прогресс загрузки."""
        dialog_manager.dialog_data.update({
            "upload_progress": step,
            "upload_total_steps": total,
            "upload_progress_text": text,
        })
        # Устанавливаем режим редактирования и обновляем окно
        dialog_manager.show_mode = ShowMode.EDIT
        try:
            await dialog_manager.show()
        except Exception as e:
            logger.debug(f"Не удалось обновить окно: {e}")
        await asyncio.sleep(0.2)  # Даём время на обновление UI

    try:
        current_step = 0

        uploads_dir = Path("uploads")
        uploads_dir.mkdir(exist_ok=True)
        file_path = uploads_dir / file_name

        # Проверяем, существует ли файл (для сравнения изменений)
        old_file_exists = file_path.exists()
        temp_old_file = None

        if old_file_exists:
            # Сохраняем старый файл временно
            temp_old_file = uploads_dir / f"temp_old_{file_name}"
            file_path.rename(temp_old_file)

        # Шаг 1: Скачиваем файл
        current_step += 1
        await update_progress(current_step, total_steps, "Загрузка файла...")
        file = await bot.get_file(document.file_id)
        await bot.download_file(file.file_path, file_path)

        actual_size = file_path.stat().st_size

        # Шаг 2: Сохраняем в БД
        current_step += 1
        await update_progress(current_step, total_steps, "Сохранение в базу данных...")
        await stp_repo.upload.add_file_history(
            file_id=document.file_id,
            file_name=file_name,
            file_size=actual_size,
            uploaded_by_user_id=message.from_user.id,
        )

        # Обновляем статус с информацией о файле
        dialog_manager.dialog_data.update({
            "upload_file_replaced": old_file_exists,
        })

        # ===== Обрабатываем файл в зависимости от типа =====

        processing_results = {}

        # Извлекаем статистику для файлов расписания
        if is_schedule:
            # Шаг 3: Извлечение статистики
            current_step += 1
            await update_progress(
                current_step, total_steps, "Анализ статистики расписания..."
            )
            new_stats = FileStatsExtractor.extract_stats(file_path)
            old_stats = (
                FileStatsExtractor.extract_stats(temp_old_file)
                if temp_old_file and temp_old_file.exists()
                else None
            )

            processing_results["new_stats"] = new_stats
            processing_results["old_stats"] = old_stats

            # Шаг 4: Обрабатываем пользователей
            current_step += 1
            await update_progress(
                current_step, total_steps, "Обработка изменений пользователей..."
            )
            if main_db:
                try:
                    from tgbot.misc.helpers import format_fullname
                    from tgbot.services.schedule.user_processor import (
                        process_fired_users_with_stats,
                        process_user_changes,
                    )

                    fired_names = await process_fired_users_with_stats(
                        [file_path], main_db
                    )
                    updated_names, new_names = await process_user_changes(
                        main_db, file_name
                    )

                    # Форматируем имена пользователей
                    formatted_fired = []
                    for name in fired_names:
                        try:
                            user = await stp_repo.employee.get_user(fullname=name)
                            if user:
                                formatted_fired.append(
                                    format_fullname(
                                        user.fullname,
                                        short=True,
                                        gender_emoji=True,
                                        username=user.username,
                                        user_id=user.user_id,
                                    )
                                )
                            else:
                                formatted_fired.append(name)
                        except Exception:
                            formatted_fired.append(name)

                    formatted_updated = []
                    for name in updated_names:
                        try:
                            user = await stp_repo.employee.get_user(fullname=name)
                            if user:
                                formatted_updated.append(
                                    format_fullname(
                                        user.fullname,
                                        short=True,
                                        gender_emoji=True,
                                        username=user.username,
                                        user_id=user.user_id,
                                    )
                                )
                            else:
                                formatted_updated.append(name)
                        except Exception:
                            formatted_updated.append(name)

                    formatted_new = []
                    for name in new_names:
                        user = await stp_repo.employee.get_user(fullname=name)
                        if user:
                            formatted_new.append(
                                format_fullname(
                                    user.fullname,
                                    short=True,
                                    gender_emoji=True,
                                    username=user.username,
                                    user_id=user.user_id,
                                )
                            )
                        else:
                            formatted_new.append(name)

                    processing_results["fired_names"] = formatted_fired
                    processing_results["updated_names"] = formatted_updated
                    processing_results["new_names"] = formatted_new
                except Exception as e:
                    logger.error(f"Ошибка обработки пользователей: {e}")

            # Шаг 5: Проверяем изменения в расписании
            if old_file_exists and temp_old_file and main_db:
                current_step += 1
                await update_progress(
                    current_step, total_steps, "Проверка изменений расписания..."
                )
                try:
                    from tgbot.misc.helpers import format_fullname
                    from tgbot.services.schedule.change_detector import (
                        ScheduleChangeDetector,
                    )

                    change_detector = ScheduleChangeDetector()

                    # Временно восстанавливаем старый файл
                    temp_old_file.rename(uploads_dir / f"old_{file_name}")

                    try:
                        (
                            changed_users,
                            notified_users,
                        ) = await change_detector.process_schedule_changes(
                            new_file_name=file_name,
                            old_file_name=f"old_{file_name}",
                            bot=bot,
                            stp_repo=stp_repo,
                        )

                        # Форматируем имена пользователей с изменениями в расписании
                        # и добавляем статус отправки уведомления
                        formatted_changed_users = []
                        for user_change in changed_users:
                            fullname = None
                            if (
                                isinstance(user_change, dict)
                                and "fullname" in user_change
                            ):
                                fullname = user_change["fullname"]
                            elif isinstance(user_change, str):
                                fullname = user_change

                            if fullname:
                                try:
                                    user = await stp_repo.employee.get_user(
                                        fullname=fullname
                                    )
                                    formatted_name = None
                                    if user:
                                        formatted_name = format_fullname(
                                            user.fullname,
                                            short=True,
                                            gender_emoji=True,
                                            username=user.username,
                                            user_id=user.user_id,
                                        )
                                    else:
                                        formatted_name = fullname

                                    # Добавляем статус уведомления (✅ или ❌)
                                    notification_status = (
                                        "✅" if fullname in notified_users else "❌"
                                    )
                                    formatted_changed_users.append({
                                        "name": formatted_name,
                                        "status": notification_status,
                                    })
                                except Exception:
                                    notification_status = (
                                        "✅" if fullname in notified_users else "❌"
                                    )
                                    formatted_changed_users.append({
                                        "name": fullname,
                                        "status": notification_status,
                                    })

                        processing_results["changed_users"] = formatted_changed_users
                        processing_results["notified_users"] = notified_users
                    finally:
                        # Удаляем временный файл
                        old_file_path = uploads_dir / f"old_{file_name}"
                        if old_file_path.exists():
                            old_file_path.unlink()

                except Exception as e:
                    logger.error(f"Ошибка проверки изменений расписания: {e}")

        # Обрабатываем файлы обучений
        elif is_studies:
            # Шаг 3: Обработка файла обучений
            current_step += 1
            await update_progress(
                current_step, total_steps, "Обработка файла обучений..."
            )
            studies_stats = await FileProcessor.process_studies_file(file_path)
            if studies_stats:
                processing_results["studies_stats"] = studies_stats

                # Шаг 4: Проверяем предстоящие обучения
                if main_db:
                    current_step += 1
                    await update_progress(
                        current_step,
                        total_steps,
                        "Отправка уведомлений об обучениях...",
                    )
                    try:
                        from tgbot.services.schedulers.studies import (
                            check_upcoming_studies,
                        )

                        notification_results = await check_upcoming_studies(
                            main_db, bot
                        )
                        processing_results["notification_results"] = (
                            notification_results
                        )
                    except Exception as e:
                        logger.error(f"Ошибка проверки обучений: {e}")

        # Очищаем временные файлы
        if temp_old_file and temp_old_file.exists():
            temp_old_file.unlink()

        # Вычисляем время загрузки
        upload_time = asyncio.get_event_loop().time() - dialog_manager.dialog_data.get(
            "upload_start_time", 0
        )

        # Сохраняем все результаты и обновляем окно
        dialog_manager.dialog_data.update({
            "upload_file_path": str(file_path),
            "upload_actual_size": actual_size,
            "upload_time": upload_time,
            "processing_results": processing_results,
            "processing_complete": True,
            "upload_progress_text": "Готово!",
        })

        # Финальное обновление окна с результатами
        dialog_manager.show_mode = ShowMode.EDIT
        try:
            await dialog_manager.show()
        except Exception as e:
            logger.debug(f"Не удалось обновить окно: {e}")

    except Exception as e:
        logger.error(f"Ошибка загрузки файла {file_name}: {e}", exc_info=True)
        dialog_manager.dialog_data["upload_error"] = (
            f"Не удалось загрузить файл: {str(e)}"
        )
        await dialog_manager.switch_to(Files.upload_error)
    finally:
        # Удаляем все временные файлы
        for temp_file in uploads_dir.glob("temp_old_*"):
            try:
                temp_file.unlink()
            except Exception as e:
                logger.error(f"[Загрузка файла] Ошибка при удалении старого файла: {e}")


async def on_upload_retry(
    _callback: CallbackQuery,
    _button: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик повторной попытки загрузки файла.

    Args:
        _callback: Callback query от пользователя
        _button: Button виджет
        dialog_manager: Менеджер диалога
    """
    # Очищаем данные предыдущей загрузки
    upload_keys = [
        key for key in dialog_manager.dialog_data.keys() if key.startswith("upload_")
    ]
    for key in upload_keys:
        dialog_manager.dialog_data.pop(key, None)

    await dialog_manager.switch_to(Files.upload)


async def on_upload_complete(
    _callback: CallbackQuery,
    _button: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик завершения процесса загрузки (возврат в меню).

    Args:
        _callback: Callback query от пользователя
        _button: Button виджет
        dialog_manager: Менеджер диалога
    """
    # Очищаем данные загрузки
    upload_keys = [
        key for key in dialog_manager.dialog_data.keys() if key.startswith("upload_")
    ]
    for key in upload_keys:
        dialog_manager.dialog_data.pop(key, None)

    await dialog_manager.switch_to(Files.menu)


async def on_view_uploaded_file(
    _callback: CallbackQuery,
    _button: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик просмотра загруженного файла.

    Args:
        _callback: Callback query от пользователя
        _button: Button виджет
        dialog_manager: Менеджер диалога
    """
    file_name = dialog_manager.dialog_data.get("upload_file_name")
    if file_name:
        dialog_manager.dialog_data["selected_file"] = file_name
        await dialog_manager.switch_to(Files.local_details)
    else:
        await _callback.answer("Файл не найден", show_alert=True)
        await dialog_manager.switch_to(Files.menu)

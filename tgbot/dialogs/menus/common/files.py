"""Генерация общих функций для загрузки файлов."""

from aiogram import F
from aiogram.enums import ContentType
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.common import sync_scroll
from aiogram_dialog.widgets.input import MessageInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Row, ScrollingGroup, Select, SwitchTo
from aiogram_dialog.widgets.text import Const, Format, List

from tgbot.dialogs.events.common.files.files import (
    close_files_dialog,
    on_download_history_file,
    on_download_local_file,
    on_file_selected,
    on_history_file_selected,
    on_remove_file,
    on_rename_file,
    on_restore_history_file,
    on_restore_selected,
    process_rename,
)
from tgbot.dialogs.events.common.files.upload import (
    on_document_uploaded,
    on_upload_complete,
    on_upload_retry,
    on_view_uploaded_file,
)
from tgbot.dialogs.getters.common.files import (
    get_all_files_history,
    get_file_history,
    get_history_file_details,
    get_local_file_details,
    get_local_files,
    get_upload_status,
)
from tgbot.dialogs.states.common.files import Files

files_window = Window(
    Const("""📂 <b>Файлы</b>

Здесь ты можешь загружать файлы, смотреть уже загруженные файлы и историю загрузок"""),
    SwitchTo(Const("📤 Загрузка файлов"), id="upload", state=Files.upload),
    Row(
        SwitchTo(Const("🗃️ Загруженные"), id="local", state=Files.local),
        SwitchTo(Const("📜 История"), id="history", state=Files.history),
    ),
    Button(Const("🏠 Домой"), id="home", on_click=close_files_dialog),
    state=Files.menu,
)


local_window = Window(
    Const("""🗃️ <b>Загруженные файлы</b>\n"""),
    List(
        Format("""{pos}. <b>{item[0]}</b>
<blockquote>📦 Размер: {item[1]}
📄 Тип: {item[2]}
📅 Изменён: {item[3]}</blockquote>\n"""),
        items="files",
        id="files_list",
        page_size=4,
    ),
    ScrollingGroup(
        Select(
            Format("{pos}. {item[0]}"),
            id="file",
            items="files",
            item_id_getter=lambda item: item[0],
            on_click=on_file_selected,
        ),
        width=2,
        height=2,
        hide_on_single_page=True,
        id="files_scroll",
        on_page_changed=sync_scroll("files_list"),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Files.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_files_dialog),
    ),
    state=Files.local,
    getter=get_local_files,
)


local_details_window = Window(
    Format("""📄 <b>Детали файла</b>

<b>Имя:</b> {file_info[name]}
<b>Размер:</b> {file_info[size]}
<b>Изменён:</b> {file_info[modified]}
<b>Записей в БД:</b> {file_info[db_count]}"""),
    Format(
        """
<b>Загружен:</b> {file_info[uploaded_at]}
<b>Пользователем:</b> {file_info[uploaded_by_fullname]}""",
        when="db_record",
    ),
    Row(
        Button(Const("🗑️ Удалить"), id="remove", on_click=on_remove_file),
        Button(Const("✏️ Переименовать"), id="rename", on_click=on_rename_file),
    ),
    Row(
        SwitchTo(Const("♻️ Восстановить"), id="restore", state=Files.restore),
        Button(Const("📥 Скачать"), id="download", on_click=on_download_local_file),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Files.local),
        Button(Const("🏠 Домой"), id="home", on_click=close_files_dialog),
    ),
    getter=get_local_file_details,
    state=Files.local_details,
)


rename_window = Window(
    Const("""✏️ <b>Переименование файла</b>

Введи новое имя для файла:"""),
    TextInput(id="new_name", on_success=process_rename),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Files.local_details),
        Button(Const("🏠 Домой"), id="home", on_click=close_files_dialog),
    ),
    state=Files.rename,
)


restore_window = Window(
    Const("""♻️ <b>Восстановление файла</b>\n"""),
    List(
        Format("""{pos}. <b>{item[3]}</b>
<blockquote>📦 Размер: {item[2]}
👤 Пользователь: {item[6]}</blockquote>\n"""),
        items="history",
        id="history_list",
        page_size=4,
    ),
    ScrollingGroup(
        Select(
            Format("{pos}. {item[3]}"),
            id="history_item",
            items="history",
            item_id_getter=lambda item: item[0],
            on_click=on_restore_selected,
        ),
        width=2,
        height=2,
        hide_on_single_page=True,
        id="history_scroll",
        on_page_changed=sync_scroll("history_list"),
    ),
    Const("<i>Выбери версию файла для восстановления</i>"),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Files.local_details),
        Button(Const("🏠 Домой"), id="home", on_click=close_files_dialog),
    ),
    getter=get_file_history,
    state=Files.restore,
)


history_window = Window(
    Const("""📜 <b>История загрузок</b>\n"""),
    List(
        Format("""{pos}. <b>{item[1]}</b>
<blockquote>📦 Размер: {item[2]}
📅 Загружен: {item[3]}
👤 Пользователь: {item[6]}</blockquote>\n"""),
        items="files",
        id="history_files_list",
        page_size=4,
    ),
    ScrollingGroup(
        Select(
            Format("{pos}. {item[1]}"),
            id="history_file",
            items="files",
            item_id_getter=lambda item: item[0],
            on_click=on_history_file_selected,
        ),
        width=2,
        height=2,
        hide_on_single_page=True,
        id="history_files_scroll",
        on_page_changed=sync_scroll("history_files_list"),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Files.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_files_dialog),
    ),
    getter=get_all_files_history,
    state=Files.history,
)


history_details_window = Window(
    Format("""📄 <b>Детали файла из истории</b>

<b>Имя:</b> {file_info[name]}
<b>Размер:</b> {file_info[size]}
<b>Загружен:</b> {file_info[uploaded_at]}
<b>Пользователем:</b> {file_info[uploaded_by_fullname]}"""),
    Row(
        Button(Const("♻️ Восстановить"), id="restore", on_click=on_restore_history_file),
        Button(Const("📥 Скачать"), id="download", on_click=on_download_history_file),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Files.history),
        Button(Const("🏠 Домой"), id="home", on_click=close_files_dialog),
    ),
    state=Files.history_details,
    getter=get_history_file_details,
)


# ===== Upload Windows =====


upload_window = Window(
    Const("""📤 <b>Загрузка файла</b>

Отправь мне любой документ, и я сохраню его в системе.

<b>Поддерживаются:</b>
• Excel файлы (.xlsx, .xls)
• CSV файлы (.csv)
• Текстовые файлы (.txt)
• PDF документы (.pdf)
• Архивы (.zip, .rar)
• И любые другие форматы

<b>Ограничения:</b>
• Максимальный размер: 20 MB

<i>Отправь файл как документ (📎), не как фото</i>"""),
    MessageInput(
        func=on_document_uploaded,
        content_types=[ContentType.DOCUMENT],
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back", state=Files.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_files_dialog),
    ),
    state=Files.upload,
)


upload_processing_window = Window(
    Format(
        """⏳ <b>Обработка файла...</b>

<b>Файл:</b> {file_name}
<b>Размер:</b> {file_size}
<b>Тип:</b> {file_type}

<b>Статус:</b> {upload_progress_text}

<i>Пожалуйста, подожди...</i>""",
        when=~F["processing_complete"],
    ),
    Format(
        """✅ <b>Файл успешно загружен!</b>

<blockquote>📄 <b>{file_name}</b>
📦 Размер: {file_size}
{file_type}
⏱ Время обработки: {upload_time} сек</blockquote>{processing_text}

<i>Файл успешно загружен</i>""",
        when="processing_complete",
    ),
    Row(
        Button(
            Const("📄 Просмотреть"),
            id="view",
            on_click=on_view_uploaded_file,
            when="processing_complete",
        ),
        Button(
            Const("📤 Загрузить ещё"),
            id="retry",
            on_click=on_upload_retry,
            when="processing_complete",
        ),
    ),
    Row(
        Button(
            Const("↩️ В меню"),
            id="menu",
            on_click=on_upload_complete,
            when="processing_complete",
        ),
        Button(
            Const("🏠 Домой"),
            id="home",
            on_click=close_files_dialog,
            when="processing_complete",
        ),
    ),
    state=Files.upload_processing,
    getter=get_upload_status,
)


upload_success_window = Window(
    Format(
        """✅ <b>Файл успешно загружен!</b>

<blockquote>📄 <b>{file_name}</b>
📦 Размер: {file_size}
{file_type}
⏱ Время обработки: {upload_time} сек</blockquote>{processing_text}

<i>Файл успешно загружен</i>""",
        when="has_processing",
    ),
    Format(
        """✅ <b>Файл успешно загружен!</b>

<blockquote>📄 <b>{file_name}</b>
📦 Размер: {file_size}
{file_type}
⏱ Время обработки: {upload_time} сек</blockquote>

<i>Файл успешно загружен
Теперь ты можешь найти его в разделе "Загруженные файлы"</i>""",
        when=~F["has_processing"],
    ),
    Row(
        Button(Const("📄 Просмотреть"), id="view", on_click=on_view_uploaded_file),
        Button(Const("📤 Загрузить ещё"), id="retry", on_click=on_upload_retry),
    ),
    Row(
        Button(Const("↩️ В меню"), id="menu", on_click=on_upload_complete),
        Button(Const("🏠 Домой"), id="home", on_click=close_files_dialog),
    ),
    state=Files.upload_success,
    getter=get_upload_status,
)


upload_error_window = Window(
    Format("""❌ <b>Ошибка загрузки файла</b>

<b>Файл:</b> {file_name}
<b>Размер:</b> {file_size}

<b>Ошибка:</b>
<blockquote>{upload_error}</blockquote>

<i>Попробуй загрузить файл снова или выбери другой файл.</i>"""),
    Row(
        Button(Const("🔄 Попробовать снова"), id="retry", on_click=on_upload_retry),
        Button(Const("↩️ В меню"), id="menu", on_click=on_upload_complete),
    ),
    Button(Const("🏠 Домой"), id="home", on_click=close_files_dialog),
    state=Files.upload_error,
    getter=get_upload_status,
)


files_dialog = Dialog(
    files_window,
    upload_window,
    upload_processing_window,
    upload_success_window,
    upload_error_window,
    local_window,
    local_details_window,
    rename_window,
    restore_window,
    history_window,
    history_details_window,
)

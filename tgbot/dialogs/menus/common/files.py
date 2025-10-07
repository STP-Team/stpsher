"""Генерация общих функций для загрузки файлов."""

from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.common import sync_scroll
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Row, ScrollingGroup, Select, SwitchTo
from aiogram_dialog.widgets.text import Const, Format, List

from tgbot.dialogs.events.common.files import (
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
from tgbot.dialogs.getters.common.files import (
    get_all_files_history,
    get_file_history,
    get_history_file_details,
    get_local_file_details,
    get_local_files,
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


files_dialog = Dialog(
    files_window,
    local_window,
    local_details_window,
    rename_window,
    restore_window,
    history_window,
    history_details_window,
)

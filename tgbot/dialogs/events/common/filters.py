"""Обработчики для функционала фильтров."""

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import ManagedRadio


async def on_filter_change(
    event: CallbackQuery,
    widget: ManagedRadio,
    dialog_manager: DialogManager,
    item_id: str,
    **_kwargs,
) -> None:
    """Универсальных обработчик фильтров для различных меню.

    Args:
        callback: Callback query от Telegram
        widget: Данные виджета Radio
        dialog_manager: Менеджер диалога
        item_id: Идентификатор выбранного фильтра
    """
    dialog_manager.dialog_data[widget.widget_id] = item_id
    await event.answer()

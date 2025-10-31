"""Обработчики для диалога настроек на бирже."""

import logging

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, ManagedRadio

logger = logging.getLogger(__name__)


async def on_reset_day_filters(
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик сброса фильтров по дням к значениям по умолчанию.

    Args:
        _event: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    try:
        # Сбрасываем фильтр дня к значению по умолчанию
        day_filter_checkbox: ManagedRadio = dialog_manager.find("day_filter")
        if day_filter_checkbox:
            await day_filter_checkbox.set_checked("all")

    except Exception as e:
        logger.error(f"[Биржа] Ошибка при сбросе фильтров по дням: {e}")


async def on_reset_shift_filters(
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик сброса фильтров по смене к значениям по умолчанию.

    Args:
        _event: Callback query от Telegram
        _widget: Виджет кнопки
        dialog_manager: Менеджер диалога
    """
    try:
        # Сбрасываем фильтр смены к значению по умолчанию
        shift_filter_checkbox: ManagedRadio = dialog_manager.find("shift_filter")
        if shift_filter_checkbox:
            await shift_filter_checkbox.set_checked("no_shift")

    except Exception as e:
        logger.error(f"[Биржа] Ошибка при сбросе фильтров по смене: {e}")

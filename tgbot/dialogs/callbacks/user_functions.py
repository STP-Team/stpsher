"""Функции для окон специалистов."""

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.api.internal import Widget

from tgbot.dialogs.states.head import HeadSG
from tgbot.dialogs.states.user import UserSG


async def on_mode_select(
    _callback: CallbackQuery,
    _widget: Widget,
    dialog_manager: DialogManager,
    item_id: str,
    **_kwargs,
) -> None:
    """Изменение режима отображения графика.

    Доступные режимы:
    - Краткий
    - Детальный

    Args:
        _callback: Callback query от Telegram
        _widget: Данные от виджета
        dialog_manager: Менеджер диалога
        item_id: Идентификатор выбранного режима
    """
    current_state = dialog_manager.current_context().state

    dialog_manager.dialog_data["schedule_mode"] = item_id

    if current_state in (UserSG.schedule_my, HeadSG.schedule_my):
        await dialog_manager.switch_to(current_state)

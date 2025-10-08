"""Обработчики для управления группой руководителя."""

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from tgbot.dialogs.states.heads.group import HeadGroupSG


async def start_group_dialog(
    _callback: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик перехода в диалог групп.

    Args:
        _callback: Callback query от Telegram
        _widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.start(
        HeadGroupSG.menu,
    )


async def close_group_dialog(
    _callback: CallbackQuery,
    _button: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик возврата к главному диалогу из диалога групп.

    Args:
        _callback: Callback query от пользователя
        _button: Button виджет
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.done()

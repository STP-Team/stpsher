from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from tgbot.dialogs.states.common.game import Game


async def start_game_dialog(
    _callback: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик перехода в диалог игры.

    Args:
        _callback: Callback query от Telegram
        _widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.start(
        Game.menu,
    )


async def close_game_dialog(
    _callback: CallbackQuery,
    _button: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик возврата к главному диалогу из диалога игры.

    Args:
        _callback: Callback query от пользователя
        _button: Button виджет
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.done()

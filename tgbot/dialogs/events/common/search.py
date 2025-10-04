"""Обработчики для функций поиска."""

import logging

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Select

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.dialogs.states.common.search import Search

logger = logging.getLogger(__name__)


async def start_search_dialog(
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
        Search.menu,
    )


async def close_search_dialog(
    _callback: CallbackQuery,
    _button: Button,
    dialog_manager: DialogManager,
) -> None:
    """Обработчик возврата к главному диалогу из диалога поиска.

    Args:
        _callback: Callback query от пользователя
        _button: Button виджет
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.done()


async def on_user_select(
    _callback: CallbackQuery, _widget: Select, dialog_manager, item_id, **_kwargs
) -> None:
    """Обработчик выбора пользователя из списка результатов поиска.

    Args:
        _callback: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
        item_id: Идентификатор выбранного пользователя
    """
    dialog_manager.dialog_data["selected_user_id"] = item_id

    # Сохраняем текущее состояние для дальнейшего возврата в текущее меню
    current_state = dialog_manager.current_context().state
    dialog_manager.dialog_data["previous_state"] = str(current_state)

    await dialog_manager.switch_to(Search.details_window)


async def on_search_query(
    _message: Message, _widget: TextInput, dialog_manager, text: str
) -> None:
    """Обработчик поискового запроса из текстового поля.

    Args:
        _message: Сообщение пользователя
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
        text: Текст сообщения пользователя
    """
    search_query = text.strip()

    if not search_query or len(search_query) < 2:
        return  # TextInput сам валидирует ввод

    try:
        stp_repo: MainRequestsRepo = dialog_manager.middleware_data.get("stp_repo")
        if not stp_repo:
            return

        # Универсальный поиск пользователей (ФИО, user_id, username)
        found_users = await stp_repo.employee.search_users(search_query, limit=50)

        if not found_users:
            # Сохраняем поисковый запрос для отображения в окне "ничего не найдено"
            dialog_manager.dialog_data["search_query"] = search_query
            # Переходим к окну "ничего не найдено"
            await dialog_manager.switch_to(Search.query_no_results)
            return

        # Сортировка результатов (сначала точные совпадения)
        sorted_users = sorted(
            found_users,
            key=lambda u: (
                # Сначала полные совпадения
                search_query.lower() not in u.fullname.lower(),
                # Потом по алфавиту
                u.fullname,
            ),
        )

        # Сохраняем результаты поиска в dialog_data
        dialog_manager.dialog_data["search_results"] = [
            (user.user_id or user.id, user.fullname, user.position or "")
            for user in sorted_users
        ]
        dialog_manager.dialog_data["search_query"] = search_query
        dialog_manager.dialog_data["total_found"] = len(sorted_users)

        # Переходим к результатам поиска
        await dialog_manager.switch_to(Search.query_results)

    except Exception as e:
        logger.error(f"[Поиск] Ошибка при попытке поиска: {e}")


async def on_back_to_menu(
    _callback: CallbackQuery, _widget: Button, dialog_manager, **_kwargs
) -> None:
    """Обработчик возврата в меню поиска из детального просмотра пользователя.

    Args:
        _callback: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.switch_to(Search.menu)

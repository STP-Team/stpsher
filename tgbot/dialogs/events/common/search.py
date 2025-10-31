"""Обработчики для функций поиска."""

import logging

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, ManagedCheckbox, ManagedRadio, Select
from stp_database import MainRequestsRepo

from tgbot.dialogs.states.common.search import Search
from tgbot.misc.dicts import roles

logger = logging.getLogger(__name__)


async def start_search_dialog(
    _event: CallbackQuery,
    _widget: Button,
    dialog_manager: DialogManager,
    **_kwargs,
) -> None:
    """Обработчик перехода в диалог групп.

    Args:
        _event: Callback query от Telegram
        _widget: Данные виджета Button
        dialog_manager: Менеджер диалога
    """
    await dialog_manager.start(
        Search.menu,
    )


async def on_back_to_menu(
    _event: CallbackQuery, _widget: Button, dialog_manager: DialogManager, **_kwargs
) -> None:
    """Обработчик возврата в меню поиска из детального просмотра пользователя.

    Args:
        _event: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
    """
    # Получаем предыдущее состояние, если оно было сохранено
    previous_state = dialog_manager.dialog_data.get("previous_state")

    # Если есть сохраненное состояние, возвращаемся к нему
    if previous_state:
        if "specialists" in previous_state:
            await dialog_manager.switch_to(Search.specialists)
        elif "heads" in previous_state:
            await dialog_manager.switch_to(Search.heads)
        elif "query_results" in previous_state:
            await dialog_manager.switch_to(Search.query_results)
        else:
            await dialog_manager.switch_to(Search.menu)
    else:
        # Если предыдущее состояние не сохранено, возвращаемся в главное меню
        await dialog_manager.switch_to(Search.menu)


async def on_user_select(
    _event: CallbackQuery, _widget: Select, dialog_manager, item_id, **_kwargs
) -> None:
    """Обработчик выбора пользователя из списка результатов поиска.

    Args:
        _event: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
        item_id: Идентификатор выбранного пользователя
    """
    dialog_manager.dialog_data["selected_user_id"] = item_id

    # Сохраняем текущее состояние для дальнейшего возврата в текущее меню
    current_state = dialog_manager.current_context().state
    dialog_manager.dialog_data["previous_state"] = str(current_state)

    # Получаем информацию о пользователе и устанавливаем состояние чекбоксов
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data.get("stp_repo")
    searched_user = await stp_repo.employee.get_users(main_id=int(item_id))

    casino_checkbox: ManagedCheckbox = dialog_manager.find("casino_access")
    if casino_checkbox:
        await casino_checkbox.set_checked(searched_user.is_casino_allowed)

    trainee_checkbox: ManagedCheckbox = dialog_manager.find("is_trainee")
    if trainee_checkbox:
        await trainee_checkbox.set_checked(searched_user.is_trainee)

    exchanges_checkbox: ManagedCheckbox = dialog_manager.find("exchanges_access")
    if exchanges_checkbox:
        await exchanges_checkbox.set_checked(not searched_user.is_exchange_banned)

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
            (user.id, user.fullname, user.position or "") for user in sorted_users
        ]
        dialog_manager.dialog_data["search_query"] = search_query
        dialog_manager.dialog_data["total_found"] = len(sorted_users)

        # Переходим к результатам поиска
        await dialog_manager.switch_to(Search.query_results)

    except Exception as e:
        logger.error(f"[Поиск] Ошибка при попытке поиска: {e}")


async def on_casino_change(
    event: CallbackQuery, widget: ManagedCheckbox, dialog_manager: DialogManager
):
    """Обработчик изменения доступа к казино.

    Args:
        event: Callback query от Telegram
        widget: Управляемый чекбокс
        dialog_manager: Менеджер диалога
    """
    try:
        stp_repo: MainRequestsRepo = dialog_manager.middleware_data.get("stp_repo")
        selected_user_id = dialog_manager.dialog_data.get("selected_user_id")

        if not stp_repo or not selected_user_id:
            await event.answer("❌ Ошибка: пользователь не выбран", show_alert=True)
            return

        # Получаем текущее состояние чекбокса
        is_casino_allowed = widget.is_checked()

        # Получаем пользователя
        searched_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))
        if not searched_user:
            searched_user = await stp_repo.employee.get_users(
                user_id=int(selected_user_id)
            )

        if not searched_user:
            await event.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Проверяем, действительно ли состояние изменилось
        # Если состояние совпадает с текущим в БД, это просто инициализация - игнорируем
        if searched_user.is_casino_allowed == is_casino_allowed:
            return

        # Обновляем доступ к казино в базе данных
        await stp_repo.employee.update_user(
            user_id=searched_user.user_id, is_casino_allowed=is_casino_allowed
        )

        # Показываем уведомление
        status_text = "включен" if is_casino_allowed else "выключен"
        await event.answer(f"✅ Доступ к казино {status_text}")

    except Exception as e:
        logger.error(f"[Казино] Ошибка при изменении доступа: {e}")
        await event.answer("❌ Ошибка при изменении доступа", show_alert=True)


async def on_trainee_change(
    event: CallbackQuery, widget: ManagedCheckbox, dialog_manager: DialogManager
):
    """Обработчик изменения статуса стажера.

    Args:
        event: Callback query от Telegram
        widget: Управляемый чекбокс
        dialog_manager: Менеджер диалога
    """
    try:
        stp_repo: MainRequestsRepo = dialog_manager.middleware_data.get("stp_repo")
        selected_user_id = dialog_manager.dialog_data.get("selected_user_id")

        if not stp_repo or not selected_user_id:
            await event.answer("❌ Ошибка: пользователь не выбран", show_alert=True)
            return

        # Получаем текущее состояние чекбокса
        is_trainee = widget.is_checked()

        # Получаем пользователя
        searched_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))
        if not searched_user:
            searched_user = await stp_repo.employee.get_users(
                user_id=int(selected_user_id)
            )

        if not searched_user:
            await event.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Проверяем, действительно ли состояние изменилось
        # Если состояние совпадает с текущим в БД, это просто инициализация - игнорируем
        if searched_user.is_trainee == is_trainee:
            return

        # Обновляем статус стажера в базе данных
        await stp_repo.employee.update_user(
            user_id=searched_user.user_id, is_trainee=is_trainee
        )

        # Показываем уведомление
        status_text = "включен" if is_trainee else "выключен"
        await event.answer(f"✅ Статус стажера {status_text}")

    except Exception as e:
        logger.error(f"[Стажер] Ошибка при изменении статуса: {e}")
        await event.answer("❌ Ошибка при изменении статуса", show_alert=True)


async def on_exchanges_change(
    event: CallbackQuery, widget: ManagedCheckbox, dialog_manager: DialogManager
):
    """Обработчик изменения доступа к обменам смен.

    Args:
        event: Callback query от Telegram
        widget: Управляемый чекбокс
        dialog_manager: Менеджер диалога
    """
    try:
        stp_repo: MainRequestsRepo = dialog_manager.middleware_data.get("stp_repo")
        selected_user_id = dialog_manager.dialog_data.get("selected_user_id")

        if not stp_repo or not selected_user_id:
            await event.answer("❌ Ошибка: пользователь не выбран", show_alert=True)
            return

        # Получаем текущее состояние чекбокса
        exchanges_access = not widget.is_checked()

        # Получаем пользователя
        searched_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))
        if not searched_user:
            searched_user = await stp_repo.employee.get_users(
                user_id=int(selected_user_id)
            )

        if not searched_user:
            await event.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Проверяем, действительно ли состояние изменилось
        # Если состояние совпадает с текущим в БД, это просто инициализация - игнорируем
        if searched_user.is_exchange_banned == exchanges_access:
            return

        # Обновляем статус стажера в базе данных
        await stp_repo.employee.update_user(
            user_id=searched_user.user_id, is_exchange_banned=exchanges_access
        )

        # Показываем уведомление
        status_text = "включен" if exchanges_access else "выключен"
        await event.answer(f"✅ Доступ к бирже {status_text}")

    except Exception as e:
        logger.error(f"[Стажер] Ошибка при изменении статуса: {e}")
        await event.answer("❌ Ошибка при изменении статуса", show_alert=True)


async def on_role_change(
    event: CallbackQuery,
    _widget: ManagedRadio,
    dialog_manager: DialogManager,
    item_id: str,
    **_kwargs,
) -> None:
    """Обработчик изменения роли пользователя.

    Args:
        event: Callback query от Telegram
        _widget: Данные виджета
        dialog_manager: Менеджер диалога
        item_id: ID выбранной роли
    """
    try:
        stp_repo: MainRequestsRepo = dialog_manager.middleware_data.get("stp_repo")
        selected_user_id = dialog_manager.dialog_data.get("selected_user_id")

        if not stp_repo or not selected_user_id:
            await event.answer("❌ Ошибка: пользователь не выбран", show_alert=True)
            return

        new_role_id = int(item_id)
        role_info = roles.get(new_role_id)

        if not role_info:
            await event.answer("❌ Ошибка: роль не найдена", show_alert=True)
            return

        # Обновляем роль пользователя
        searched_user = await stp_repo.employee.get_users(main_id=int(selected_user_id))
        if not searched_user:
            searched_user = await stp_repo.employee.get_users(
                user_id=int(selected_user_id)
            )

        if not searched_user:
            await event.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Проверяем, изменилась ли роль
        if searched_user.role == new_role_id:
            return

        # Обновляем роль в базе данных
        await stp_repo.employee.update_user(
            user_id=searched_user.user_id, role=new_role_id
        )

        # Показываем уведомление о смене роли
        await event.answer(
            f"✅ Роль изменена на: {role_info['emoji']} {role_info['name']}"
        )

        # Остаемся на том же окне, чтобы показать обновленный список
        await dialog_manager.switch_to(Search.details_access_level_window)

    except Exception as e:
        logger.error(f"[Смена роли] Ошибка при изменении роли: {e}")
        await event.answer("❌ Ошибка при изменении роли", show_alert=True)


async def on_schedule_mode_select(
    _event: CallbackQuery,
    _widget,
    dialog_manager: DialogManager,
    item_id: str,
    **_kwargs,
) -> None:
    """Изменение режима отображения графика в поиске.

    Args:
        _event: Callback query от Telegram
        _widget: Данные от виджета
        dialog_manager: Менеджер диалога
        item_id: Идентификатор выбранного режима
    """
    dialog_manager.dialog_data["schedule_mode"] = item_id
    await dialog_manager.switch_to(Search.details_schedule_window)

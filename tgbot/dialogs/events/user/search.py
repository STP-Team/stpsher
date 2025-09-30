from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.misc.states.dialogs.gok import GokSG
from tgbot.misc.states.dialogs.head import HeadSG
from tgbot.misc.states.dialogs.mip import MipSG
from tgbot.misc.states.dialogs.user import UserSG


def get_state_group_from_dialog_manager(dialog_manager):
    """Determine which state group to use based on dialog manager state"""
    current_state = dialog_manager.current_context().state
    if hasattr(current_state, "group"):
        state_group = current_state.group
        if state_group == HeadSG:
            return HeadSG
        elif state_group == GokSG:
            return GokSG
        elif state_group == MipSG:
            return MipSG
    return UserSG


async def on_user_select(callback, widget, dialog_manager, item_id, **kwargs):
    """
    Обработчик выбора пользователя из списка поиска
    """
    dialog_manager.dialog_data["selected_user_id"] = item_id

    # Store the current state as the previous state for back navigation
    current_state = dialog_manager.current_context().state
    dialog_manager.dialog_data["previous_state"] = current_state

    # Determine which state group to use based on current state
    state_group = get_state_group_from_dialog_manager(dialog_manager)
    await dialog_manager.switch_to(state_group.search_user_detail)


async def on_search_query(message, widget, dialog_manager, text: str):
    """
    Обработчик поискового запроса из текстового поля
    """
    search_query = text.strip()

    if not search_query or len(search_query) < 2:
        return  # TextInput will handle validation

    try:
        # Получаем репозиторий из middleware
        stp_repo: MainRequestsRepo = dialog_manager.middleware_data.get("stp_repo")
        if not stp_repo:
            return

        # Универсальный поиск пользователей (ФИО, user_id, username)
        found_users = await stp_repo.employee.search_users(search_query, limit=50)

        if not found_users:
            # Сохраняем поисковый запрос для отображения в окне "ничего не найдено"
            dialog_manager.dialog_data["search_query"] = search_query
            # Переходим к окну "ничего не найдено"
            state_group = get_state_group_from_dialog_manager(dialog_manager)
            await dialog_manager.switch_to(state_group.search_no_results)
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
        state_group = get_state_group_from_dialog_manager(dialog_manager)
        await dialog_manager.switch_to(state_group.search_result)

    except Exception:
        pass  # Fail silently for TextInput validation


async def on_back_from_user_detail(callback, widget, dialog_manager, **kwargs):
    """
    Обработчик возврата назад из детального просмотра пользователя
    """
    # Get the previous state from dialog data
    previous_state = dialog_manager.dialog_data.get("previous_state")

    if previous_state:
        # Navigate back to the previous state
        await dialog_manager.switch_to(previous_state)
    else:
        # Fallback to search results if no previous state stored
        state_group = get_state_group_from_dialog_manager(dialog_manager)
        await dialog_manager.switch_to(state_group.search_result)

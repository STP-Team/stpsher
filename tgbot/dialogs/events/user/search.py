from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.misc.states.user.main import UserSG


async def on_user_select(callback, widget, dialog_manager, item_id, **kwargs):
    """
    Обработчик выбора пользователя из списка поиска
    """
    dialog_manager.dialog_data["selected_user_id"] = item_id
    await dialog_manager.switch_to(UserSG.search_user_detail)


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
            await dialog_manager.switch_to(UserSG.search_no_results)
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
        await dialog_manager.switch_to(UserSG.search_result)

    except Exception:
        pass  # Fail silently for TextInput validation

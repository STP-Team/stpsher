"""Генерация окон поиска для специалистов."""

from tgbot.dialogs.menus.common.search import create_search_windows
from tgbot.dialogs.states.user import UserSG

(
    search_window,
    search_specialists_window,
    search_heads_window,
    search_query_window,
    search_results_window,
    search_no_results_window,
    search_user_info_window,
) = create_search_windows(UserSG, UserSG.menu)

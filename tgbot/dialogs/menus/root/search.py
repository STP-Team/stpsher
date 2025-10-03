"""Генерация окон поиска для root."""

from tgbot.dialogs.menus.common.search import create_search_windows
from tgbot.misc.states.dialogs.root import RootSG

(
    search_window,
    search_specialists_window,
    search_heads_window,
    search_query_window,
    search_results_window,
    search_no_results_window,
    search_user_info_window,
) = create_search_windows(RootSG, RootSG.menu)

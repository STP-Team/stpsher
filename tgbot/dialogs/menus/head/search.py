"""Генерация окон поиска для руководителей."""

from tgbot.dialogs.menus.common.search import create_search_windows
from tgbot.misc.states.dialogs.head import HeadSG

(
    head_search_window,
    head_search_specialists_window,
    head_search_heads_window,
    head_search_query_window,
    head_search_results_window,
    head_search_no_results_window,
    head_search_user_info_window,
) = create_search_windows(HeadSG, HeadSG.menu)

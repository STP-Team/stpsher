"""Генерация окна достижений для специалистов."""

from tgbot.dialogs.getters.common.game.achievements import (
    role_based_achievements_filter_getter,
)
from tgbot.dialogs.menus.common.game.achievements import create_achievements_windows
from tgbot.dialogs.states.user import UserSG

(game_achievements_window,) = create_achievements_windows(
    UserSG, UserSG.game, role_based_achievements_filter_getter
)

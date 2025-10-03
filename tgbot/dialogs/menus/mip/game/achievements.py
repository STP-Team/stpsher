"""Генерация окна достижений для МИП."""

from tgbot.dialogs.getters.common.game.achievements import (
    role_based_achievements_filter_getter,
)
from tgbot.dialogs.menus.common.game.achievements import create_achievements_windows
from tgbot.misc.states.dialogs.mip import MipSG

(game_achievements_window,) = create_achievements_windows(
    MipSG, MipSG.game, role_based_achievements_filter_getter
)

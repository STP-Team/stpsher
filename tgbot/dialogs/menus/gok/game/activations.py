"""Генерация окна активаций предметов для ГОК."""

from tgbot.dialogs.menus.common.game.activations import create_activations_windows
from tgbot.dialogs.states.gok import GokSG

(
    game_activations_window,
    game_activation_detail_window,
    game_activations_empty_window,
) = create_activations_windows(GokSG, GokSG.game)

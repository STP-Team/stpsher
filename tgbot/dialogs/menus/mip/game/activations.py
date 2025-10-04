"""Генерация окна активаций предметов для МИП."""

from tgbot.dialogs.menus.common.game.activations import create_activations_windows
from tgbot.dialogs.states.mip import MipSG

(
    game_activations_window,
    game_activation_detail_window,
    game_activations_empty_window,
) = create_activations_windows(MipSG, MipSG.menu)

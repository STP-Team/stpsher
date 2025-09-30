from tgbot.dialogs.menus.common.activations import create_activations_windows
from tgbot.misc.states.dialogs.gok import GokSG

(
    game_activations_window,
    game_activation_detail_window,
    game_activations_empty_window,
) = create_activations_windows(GokSG, GokSG.game)

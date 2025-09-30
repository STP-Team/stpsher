from tgbot.dialogs.menus.common.game.activations import create_activations_windows
from tgbot.misc.states.dialogs.user import UserSG

(
    game_activations_window,
    game_activation_detail_window,
    game_activations_empty_window,
) = create_activations_windows(UserSG, UserSG.game)

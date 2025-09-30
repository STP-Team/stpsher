from tgbot.dialogs.getters.common.game.shop import role_based_product_filter_getter
from tgbot.dialogs.menus.common.game.products import create_products_window
from tgbot.misc.states.dialogs.gok import GokSG

game_products_window = create_products_window(
    GokSG, GokSG.game, role_based_product_filter_getter
)

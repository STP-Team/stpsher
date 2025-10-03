"""Генерация окна предметов для МИП."""

from tgbot.dialogs.getters.common.game.shop import role_based_product_filter_getter
from tgbot.dialogs.menus.common.game.products import create_products_window
from tgbot.misc.states.dialogs.mip import MipSG

game_products_window = create_products_window(
    MipSG, MipSG.game, role_based_product_filter_getter
)

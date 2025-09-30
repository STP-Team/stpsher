from aiogram_dialog.widgets.kbd import (
    Button,
    Row,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.events.user.inventory import use_product
from tgbot.dialogs.events.user.shop import (
    on_confirm_purchase,
    on_sell_product,
)
from tgbot.dialogs.getters.common.game.shop import role_based_product_filter_getter
from tgbot.dialogs.getters.user.game.shop import confirmation_getter, success_getter
from tgbot.dialogs.menus.common.game.products import create_products_window
from tgbot.misc.states.dialogs.user import UserSG

game_shop_window = create_products_window(
    UserSG, UserSG.game, role_based_product_filter_getter
)

game_shop_confirm_window = Window(
    Format("""<b>🎯 Покупка предмета:</b> {product_name}

<b>📝 Описание</b>
{product_description}

<b>📍 Количество использований:</b> {product_count}

<b>✨ Баланс</b>
• Текущий: {user_balance} баллов
• Спишется: {product_cost} баллов
• Останется: {balance_after_purchase} баллов

<i>Купленные предметы можно найти в <b>🎒 Инвентаре</b></i>"""),
    Button(
        Const("✅ Купить"),
        id="confirm_buy",
        on_click=on_confirm_purchase,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="menu", state=UserSG.game_products),
        SwitchTo(Const("🏠 Домой"), id="home", state=UserSG.menu),
    ),
    getter=confirmation_getter,
    state=UserSG.game_shop_confirm,
)

game_shop_success_window = Window(
    Format("""<b>✅ Приобретен предмет:</b> {product_name}

<b>📍 Количество активаций:</b> {product_count}

<b>✨ Баланс</b>
• Был: {user_balance} баллов
• Списано: {product_cost} баллов
• Стало: {new_balance} баллов

<b>📝 Описание</b>
{product_description}

<i>🎯 Ты можешь использовать его сейчас или позже в <b>🎒 Инвентаре</b></i>"""),
    Row(
        Button(
            Const("🎯 Использовать"),
            id="use_product",
            on_click=use_product,
        ),
        Button(
            Const("💸 Продать"),
            id="sell_product",
            on_click=on_sell_product,
        ),
    ),
    Row(
        SwitchTo(Const("🎒 Инвентарь"), id="inventory", state=UserSG.game_inventory),
        SwitchTo(Const("💎 Магазин"), id="inventory", state=UserSG.game_products),
    ),
    Row(
        SwitchTo(Const("🏮 К игре"), id="to_game", state=UserSG.game),
        SwitchTo(Const("🏠 Домой"), id="home", state=UserSG.menu),
    ),
    getter=success_getter,
    state=UserSG.game_shop_success,
)

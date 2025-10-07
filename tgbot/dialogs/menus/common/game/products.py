"""Генерация общих функций для просмотра списка предметов."""

from aiogram import F
from aiogram_dialog.widgets.common import sync_scroll
from aiogram_dialog.widgets.kbd import (
    Button,
    CurrentPage,
    FirstPage,
    LastPage,
    NextPage,
    PrevPage,
    Radio,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format, List
from aiogram_dialog.window import Window

from tgbot.dialogs.events.common.filters import on_filter_change
from tgbot.dialogs.events.common.game.game import close_game_dialog
from tgbot.dialogs.events.common.game.inventory import use_product
from tgbot.dialogs.events.common.game.shop import (
    on_confirm_purchase,
    on_product_click,
    on_sell_product,
)
from tgbot.dialogs.filters.common.game_filters import (
    product_filter_getter,
)
from tgbot.dialogs.getters.common.game.shop import confirmation_getter, success_getter
from tgbot.dialogs.states.common.game import Game

products_window = Window(
    Format(
        """💎 <b>Магазин</b>

<b>✨ Твой баланс:</b> {user_balance} баллов\n""",
        when="is_user",
    ),
    Const("""👏 <b>Предметы</b>\n""", when=~F["is_user"]),
    List(
        Format("""{pos}. <b>{item[1]}</b>
<blockquote>💵 Стоимость: {item[4]} баллов
📝 Описание: {item[2]}
📍 Активаций: {item[3]}</blockquote>\n"""),
        items="products",
        id="shop_products",
        page_size=4,
    ),
    ScrollingGroup(
        Select(
            Format("{pos}. {item[1]}"),
            id="product",
            items="products",
            item_id_getter=lambda item: item[0],
            on_click=on_product_click,
        ),
        width=2,
        height=2,
        hide_on_single_page=True,
        id="shop_scroll",
        on_page_changed=sync_scroll("shop_products"),
        when="is_user",
    ),
    Row(
        FirstPage(
            scroll="shop_products",
            text=Format("1"),
        ),
        PrevPage(
            scroll="shop_products",
            text=Format("<"),
        ),
        CurrentPage(
            scroll="shop_products",
            text=Format("{current_page1}"),
        ),
        NextPage(
            scroll="shop_products",
            text=Format(">"),
        ),
        LastPage(
            scroll="shop_products",
            text=Format("{target_page1}"),
        ),
        when=~F["is_user"],
    ),
    Row(
        Radio(
            Format("🔘 {item[1]}"),
            Format("⚪️ {item[1]}"),
            id="product_filter",
            item_id_getter=lambda item: item[0],
            items=[("available", "Доступные"), ("all", "Все предметы")],
            on_click=on_filter_change,
        ),
        when="is_user",
    ),
    Row(
        Radio(
            Format("🔘 {item[1]}"),
            Format("⚪️ {item[1]}"),
            id="product_division_filter",
            item_id_getter=lambda item: item[0],
            items="division_radio_data",
            on_click=on_filter_change,
        ),
        when=~F["is_user"],
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="menu", state=Game.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_game_dialog),
    ),
    getter=product_filter_getter,
    state=Game.products,
)


products_confirm_window = Window(
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
        SwitchTo(Const("↩️ Назад"), id="menu", state=Game.products),
        Button(Const("🏠 Домой"), id="home", on_click=close_game_dialog),
    ),
    getter=confirmation_getter,
    state=Game.products_confirm,
)

products_success_window = Window(
    Format(""""<b>✅ Приобретен предмет:</b> {product_name}

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
        SwitchTo(Const("🎒 Инвентарь"), id="inventory", state=Game.inventory),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="to_game", state=Game.menu),
        Button(Const("🏠 Домой"), id="home", on_click=close_game_dialog),
    ),
    getter=success_getter,
    state=Game.products_success,
)

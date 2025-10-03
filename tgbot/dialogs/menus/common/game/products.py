"""Генерация общих функций для просмотра списка предметов."""

from aiogram import F
from aiogram_dialog.widgets.common import sync_scroll
from aiogram_dialog.widgets.kbd import (
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
from tgbot.dialogs.events.user.shop import on_product_click


def create_products_window(state_group, menu_state, product_filter_getter):
    """Создает окна для просмотра списка предметов.

    Args:
        state_group: Группа состояний, используемая для переключения окон
        menu_state: Состояние главного меню
        product_filter_getter: Геттер для фильтрации списка предметов

    Returns:
        Отфильтрованный список предметов в зависимости от роли сотрудника
    """
    shop_window = Window(
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
                id="product_filter",
                item_id_getter=lambda item: item[0],
                items="division_radio_data",
                on_click=on_filter_change,
            ),
            when=~F["is_user"],
        ),
        Row(
            SwitchTo(Const("↩️ Назад"), id="menu", state=menu_state),
            SwitchTo(Const("🏠 Домой"), id="home", state=menu_state),
        ),
        getter=product_filter_getter,
        state=state_group.game_products,
    )

    return shop_window

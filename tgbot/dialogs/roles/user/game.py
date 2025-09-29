from aiogram_dialog.widgets.common import sync_scroll
from aiogram_dialog.widgets.kbd import (
    Button,
    Radio,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format, List
from aiogram_dialog.window import Window

from tgbot.dialogs.events.user.game import (
    on_confirm_purchase,
    on_filter_change,
    on_inventory_cancel_activation,
    on_inventory_product_click,
    on_inventory_sell_product,
    on_inventory_use_product,
    on_product_click,
    on_sell_product,
)
from tgbot.dialogs.getters.user.game_getters import (
    confirmation_getter,
    inventory_detail_getter,
    inventory_filter_getter,
    product_filter_getter,
    success_getter,
)
from tgbot.dialogs.getters.user.user_getters import game_getter
from tgbot.misc.states.user.main import UserSG


def get_status_emoji(status: str) -> str:
    """Возвращает эмодзи в зависимости от статуса"""
    status_emojis = {
        "stored": "📦",
        "review": "⏳",
        "used_up": "🔒",
    }
    return status_emojis.get(status, "❓")


game_window = Window(
    Format("""🏮 <b>Игра</b>

{level_info}

<blockquote expandable><b>✨ Баланс</b>
Всего заработано: {achievements_sum} баллов
Всего потрачено: {purchases_sum} баллов</blockquote>"""),
    SwitchTo(Const("💎 Магазин"), id="shop", state=UserSG.game_shop),
    Row(
        SwitchTo(
            Const("🎒 Инвентарь"),
            id="inventory",
            state=UserSG.game_inventory,
        ),
        Button(
            Const("🎲 Казино"),
            id="casino",
        ),
    ),
    Button(
        Const("🎯 Достижения"),
        id="achievements",
    ),
    Button(
        Const("📜 История баланса"),
        id="history",
    ),
    SwitchTo(Const("↩️ Назад"), id="menu", state=UserSG.menu),
    getter=game_getter,
    state=UserSG.game,
)

shop_window = Window(
    Format("""💎 <b>Магазин</b>

<b>✨ Твой баланс:</b> {user_balance} баллов\n"""),
    List(
        Format("""{pos}. <b>{item[1]}</b>
<blockquote>💵 Стоимость: {item[3]} баллов
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
            item_id_getter=lambda item: item[0],  # Идентификатор предмета
            on_click=on_product_click,
        ),
        width=2,
        height=2,
        hide_on_single_page=True,
        id="shop_scroll",
        on_page_changed=sync_scroll("shop_products"),
    ),
    Row(
        Radio(
            Format("🔘 {item[1]}"),
            Format("⚪️ {item[1]}"),
            id="shop_filter",
            item_id_getter=lambda item: item[0],
            items=[("available", "Доступные"), ("all", "Все предметы")],
            on_click=on_filter_change,
        ),
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="menu", state=UserSG.game),
        SwitchTo(Const("🏠 Домой"), id="home", state=UserSG.menu),
    ),
    getter=product_filter_getter,
    preview_data=product_filter_getter,
    state=UserSG.game_shop,
)

confirm_window = Window(
    Format("""<b>🎯 Покупка предмета:</b> {product_name}

<b>📝 Описание</b>
{product_description}

<b>📍 Количество использований:</b> {product_count}

<b>✨ Баланс</b>
• Текущий: {user_balance} баллов
• Спишется: {product_cost} баллов
• Останется: {balance_after_purchase} баллов

<i>Купленные предметы можно найти в <b>🎒 Инвентаре</b></i>"""),
    Row(
        Button(
            Const("✅ Купить"),
            id="confirm_buy",
            on_click=on_confirm_purchase,
        ),
        SwitchTo(
            Const("❌ Отмена"),
            id="cancel_buy",
            state=UserSG.game_shop,
        ),
    ),
    getter=confirmation_getter,
    state=UserSG.game_shop_confirm,
)

success_window = Window(
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
            Const("💸 Продать"),
            id="sell_product",
            on_click=on_sell_product,
        ),
        SwitchTo(
            Const("🛒 В магазин"),
            id="back_to_shop",
            state=UserSG.game_shop,
        ),
    ),
    Row(
        SwitchTo(Const("🏮 К игре"), id="to_game", state=UserSG.game),
        SwitchTo(Const("🏠 Домой"), id="home", state=UserSG.menu),
    ),
    getter=success_getter,
    state=UserSG.game_shop_success,
)


inventory_window = Window(
    Format("""🎒 <b>Инвентарь</b>

Здесь ты найдешь все свои покупки, а так же их статус и многое другое

<i>Всего предметов приобретено: {total_bought}</i>"""),
    ScrollingGroup(
        Select(
            Format("{item[1]}"),
            id="inventory_product",
            items="products",
            item_id_getter=lambda item: item[0],  # ID покупки для обработчика клика
            on_click=on_inventory_product_click,
        ),
        width=2,
        height=2,
        hide_on_single_page=True,
        id="inventory_scroll",
    ),
    Radio(
        Format("🔘 {item[1]}"),
        Format("⚪️ {item[1]}"),
        id="inventory_filter",
        item_id_getter=lambda item: item[0],
        items=[
            ("all", "📋 Все"),
            ("stored", f"{get_status_emoji('stored')} Готовые"),
            ("review", f"{get_status_emoji('review')} На проверке"),
            ("used_up", f"{get_status_emoji('used_up')} Использованы"),
        ],
        on_click=on_filter_change,
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="menu", state=UserSG.game),
        SwitchTo(Const("🏠 Домой"), id="home", state=UserSG.menu),
    ),
    getter=inventory_filter_getter,
    preview_data=inventory_filter_getter,
    state=UserSG.game_inventory,
)


inventory_detail_window = Window(
    Format("""
<b>🛍️ Предмет:</b> {product_name}

<b>📊 Статус</b>
{status_name}

<b>📍 Активаций</b>
{usage_count} из {product_count}

<b>💵 Стоимость</b>
{product_cost} баллов

<b>📝 Описание</b>
{product_description}

<blockquote expandable><b>📅 Дата покупки</b>
{bought_at}</blockquote>{comment_text}{updated_by_text}"""),
    # Кнопки действий с предметом
    Button(
        Const("🎯 Использовать"),
        id="use_product",
        on_click=on_inventory_use_product,
        when="can_use",
    ),
    Button(
        Const("💸 Вернуть"),
        id="sell_product",
        on_click=on_inventory_sell_product,
        when="can_sell",
    ),
    Button(
        Const("✋🏻 Отменить активацию"),
        id="cancel_activation",
        on_click=on_inventory_cancel_activation,
        when="can_cancel",
    ),
    Row(
        SwitchTo(Const("↩️ Назад"), id="back_to_inventory", state=UserSG.game_inventory),
        SwitchTo(Const("🏠 Домой"), id="home", state=UserSG.menu),
    ),
    getter=inventory_detail_getter,
    state=UserSG.game_inventory_detail,
)

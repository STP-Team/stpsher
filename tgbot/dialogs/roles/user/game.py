from aiogram_dialog import DialogManager
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

from infrastructure.database.repo.STP.requests import MainRequestsRepo
from tgbot.dialogs.getters.user.game_getters import (
    confirmation_getter,
    product_filter_getter,
    success_getter,
)
from tgbot.dialogs.getters.user.user_getters import game_getter
from tgbot.misc.states.user.main import UserSG


async def on_product_click(
    callback, widget, dialog_manager: DialogManager, item_id, **kwargs
):
    """
    Обработчик нажатия на продукт - переход к подтверждению покупки
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user = dialog_manager.middleware_data["user"]

    try:
        product_info = await stp_repo.product.get_product(item_id)
    except Exception as e:
        print(e)
        await callback.answer(
            "❌ Ошибка получения информации о предмете", show_alert=True
        )
        return

    # Получаем баланс пользователя
    user_balance = await stp_repo.transaction.get_user_balance(user.user_id)

    # Проверяем, достаточно ли баллов
    if user_balance < product_info.cost:
        await callback.answer(
            f"❌ Недостаточно баллов!\nУ тебя: {user_balance} баллов\nНужно: {product_info.cost} баллов",
            show_alert=True,
        )
        return

    # Сохраняем информацию о выбранном продукте в dialog_data
    dialog_manager.dialog_data["selected_product"] = {
        "id": product_info.id,
        "name": product_info.name,
        "description": product_info.description,
        "cost": product_info.cost,
        "count": product_info.count,
    }
    dialog_manager.dialog_data["user_balance"] = user_balance

    # Переходим к окну подтверждения
    await dialog_manager.switch_to(UserSG.game_shop_confirm)


async def on_filter_change(callback, widget, dialog_manager, item_id, **kwargs):
    """
    Обработчик нажатия на фильтр
    """
    dialog_manager.dialog_data["product_filter"] = item_id
    await callback.answer()


async def on_confirm_purchase(
    callback, widget, dialog_manager: DialogManager, **kwargs
):
    """
    Обработчик подтверждения покупки
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user = dialog_manager.middleware_data["user"]
    product_info = dialog_manager.dialog_data["selected_product"]

    # Получаем актуальный баланс пользователя
    user_balance = await stp_repo.transaction.get_user_balance(user.user_id)

    if user_balance < product_info["cost"]:
        await callback.answer(
            f"❌ Недостаточно баллов!\nУ тебя: {user_balance}, нужно: {product_info['cost']}",
            show_alert=True,
        )
        return

    try:
        # Создаем покупку со статусом "stored"
        new_purchase = await stp_repo.purchase.add_purchase(
            user_id=user.user_id, product_id=product_info["id"], status="stored"
        )
        await stp_repo.transaction.add_transaction(
            user_id=user.user_id,
            transaction_type="spend",
            source_type="product",
            source_id=product_info["id"],
            amount=product_info["cost"],
            comment=f"Автоматическая покупка предмета {product_info['name']}",
        )

        # Сохраняем информацию о покупке
        dialog_manager.dialog_data["new_purchase"] = {"id": new_purchase.id}
        dialog_manager.dialog_data["new_balance"] = user_balance - product_info["cost"]

        # Переходим к окну успешной покупки
        await dialog_manager.switch_to(UserSG.game_shop_success)

    except Exception:
        await callback.answer("❌ Ошибка при покупке предмета", show_alert=True)


async def on_sell_product(callback, widget, dialog_manager: DialogManager, **kwargs):
    """
    Обработчик продажи предмета
    """
    stp_repo: MainRequestsRepo = dialog_manager.middleware_data["stp_repo"]
    user = dialog_manager.middleware_data["user"]
    new_purchase = dialog_manager.dialog_data["new_purchase"]
    product_info = dialog_manager.dialog_data["selected_product"]

    try:
        success = await stp_repo.purchase.delete_user_purchase(new_purchase["id"])
        await stp_repo.transaction.add_transaction(
            user_id=user.user_id,
            transaction_type="earn",
            source_type="product",
            source_id=product_info["id"],
            amount=product_info["cost"],
            comment=f"Возврат предмета: {product_info['name']}",
        )

        if success:
            await callback.answer(
                f"✅ Продано: {product_info['name']}.\nВозвращено: {product_info['cost']} баллов"
            )
            # Возвращаемся в магазин
            await dialog_manager.switch_to(UserSG.game_shop)
        else:
            await callback.answer("❌ Ошибка при продаже предмета", show_alert=True)

    except Exception:
        await callback.answer("❌ Ошибка при продаже предмета", show_alert=True)


game_window = Window(
    Format("""🏮 <b>Игра</b>

{level_info}

<blockquote expandable><b>✨ Баланс</b>
Всего заработано: {achievements_sum} баллов
Всего потрачено: {purchases_sum} баллов</blockquote>"""),
    SwitchTo(Const("💎 Магазин"), id="shop", state=UserSG.game_shop),
    Row(
        Button(
            Const("🎒 Инвентарь"),
            id="inventory",
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

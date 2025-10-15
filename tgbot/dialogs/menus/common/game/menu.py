"""Генерация общих функций для просмотра списка достижений."""

from typing import Any

from aiogram import F
from aiogram_dialog import Dialog, DialogManager
from aiogram_dialog.widgets.kbd import (
    Button,
    ManagedRadio,
    Row,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.window import Window

from tgbot.dialogs.events.common.game.game import close_game_dialog
from tgbot.dialogs.getters.common.game.game import game_getter
from tgbot.dialogs.menus.common.game.achievements import achievements_window
from tgbot.dialogs.menus.common.game.activations import (
    activation_details_window,
    activations_window,
    no_activations_window,
)
from tgbot.dialogs.menus.common.game.casino import (
    casino_bowling_window,
    casino_darts_window,
    casino_dice_window,
    casino_result_window,
    casino_slots_window,
    casino_waiting_window,
    casino_window,
)
from tgbot.dialogs.menus.common.game.history import (
    history_details_window,
    history_window,
)
from tgbot.dialogs.menus.common.game.inventory import (
    inventory_details_window,
    inventory_window,
)
from tgbot.dialogs.menus.common.game.products import (
    products_confirm_window,
    products_success_window,
    products_window,
)
from tgbot.dialogs.states.common.game import Game

game_window = Window(
    Const("🏮 <b>Игра</b>"),
    Format(
        """\n{level_info}

<blockquote expandable><b>✨ Баланс</b>
Всего заработано: {achievements_sum} баллов
Всего потрачено: {purchases_sum} баллов</blockquote>""",
        when="is_user",
    ),
    Const(
        """\nЗдесь ты можешь:
- Подтверждать/отклонять покупки специалистов
- Просматривать список достижений
- Просматривать список предметов""",
        when=~F["is_user"],
    ),
    SwitchTo(Const("💎 Магазин"), id="products", state=Game.products, when="is_user"),
    SwitchTo(
        Const("✍️ Активация предметов"),
        id="products_activation",
        state=Game.activations,
        when="activations_access",
    ),
    Row(
        SwitchTo(
            Const("🎒 Инвентарь"), id="inventory", state=Game.inventory, when="is_user"
        ),
        SwitchTo(Const("🎲 Казино"), id="casino", state=Game.casino, when="is_user"),
    ),
    SwitchTo(
        Const("🎯 Достижения"),
        id="achievements",
        state=Game.achievements,
    ),
    SwitchTo(
        Const("👏 Предметы"), id="products", state=Game.products, when=~F["is_user"]
    ),
    SwitchTo(
        Const("📜 История баланса"), id="history", state=Game.history, when="is_user"
    ),
    Button(Const("↩️ Назад"), id="menu", on_click=close_game_dialog),
    getter=game_getter,
    state=Game.menu,
)


async def on_start(_on_start: Any, dialog_manager: DialogManager, **_kwargs):
    """Установка параметров диалога по умолчанию при запуске.

    Args:
        _on_start: Дополнительные параметры запуска диалога
        dialog_manager: Менеджер диалога
    """
    # Фильтр предметов магазина на "Доступные"
    product_filter: ManagedRadio = dialog_manager.find("product_filter")
    await product_filter.set_checked("available")

    # Фильтр инвентаря на "Все"
    inventory_filter: ManagedRadio = dialog_manager.find("inventory_filter")
    await inventory_filter.set_checked("all")

    # Фильтр достижений по должностям на "Все"
    achievement_position_filter: ManagedRadio = dialog_manager.find(
        "achievement_position_filter"
    )
    await achievement_position_filter.set_checked("all")

    # Фильтр достижений по периоду начисления на "Все"
    achievement_period_filter: ManagedRadio = dialog_manager.find(
        "achievement_period_filter"
    )
    await achievement_period_filter.set_checked("all")

    # Фильтр достижений по направлению на "Все"
    achievement_division_filter: ManagedRadio = dialog_manager.find(
        "achievement_division_filter"
    )
    await achievement_division_filter.set_checked("all")

    # Фильтр предметов по направлению на "Все"
    product_division_filter: ManagedRadio = dialog_manager.find(
        "product_division_filter"
    )
    await product_division_filter.set_checked("all")

    # Фильтр истории баланса по типу операции на "Все"
    history_type_filter: ManagedRadio = dialog_manager.find("history_type_filter")
    await history_type_filter.set_checked("all")

    # Фильтр истории баланса по источнику операции на "Все"
    history_source_filter: ManagedRadio = dialog_manager.find("history_source_filter")
    await history_source_filter.set_checked("all")


game_dialog = Dialog(
    game_window,
    achievements_window,
    products_window,
    products_confirm_window,
    products_success_window,
    activations_window,
    no_activations_window,
    activation_details_window,
    inventory_window,
    inventory_details_window,
    history_window,
    history_details_window,
    casino_window,
    casino_slots_window,
    casino_dice_window,
    casino_darts_window,
    casino_bowling_window,
    casino_waiting_window,
    casino_result_window,
    on_start=on_start,
)

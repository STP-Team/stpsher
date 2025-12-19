"""Импорт всех диалогов и добавление их в dialogs_list."""

from tgbot.dialogs.menus.admin.main import admin_dialog
from tgbot.dialogs.menus.common.broadcast import broadcast_dialog
from tgbot.dialogs.menus.common.exchanges.create.buy import exchanges_buy_dialog
from tgbot.dialogs.menus.common.exchanges.create.sell import exchanges_sell_dialog
from tgbot.dialogs.menus.common.exchanges.exchanges import exchanges_dialog
from tgbot.dialogs.menus.common.exchanges.stats import exchanges_stats_dialog
from tgbot.dialogs.menus.common.exchanges.subscriptions import (
    exchanges_subscriptions_dialog,
)
from tgbot.dialogs.menus.common.files import files_dialog
from tgbot.dialogs.menus.common.game.menu import game_dialog
from tgbot.dialogs.menus.common.groups.groups import groups_dialog
from tgbot.dialogs.menus.common.kpi import kpi_dialog
from tgbot.dialogs.menus.common.schedules import schedules_dialog
from tgbot.dialogs.menus.common.search import search_dialog
from tgbot.dialogs.menus.gok.main import gok_dialog
from tgbot.dialogs.menus.head.group import head_group_dialog
from tgbot.dialogs.menus.head.main import head_dialog
from tgbot.dialogs.menus.mip.main import mip_dialog
from tgbot.dialogs.menus.root.main import root_dialog
from tgbot.dialogs.menus.user.main import user_dialog

dialogs_list = [
    user_dialog,
    head_dialog,
    head_group_dialog,
    admin_dialog,
    gok_dialog,
    mip_dialog,
    root_dialog,
]

common_dialogs_list = [
    schedules_dialog,
    exchanges_dialog,
    exchanges_buy_dialog,
    exchanges_sell_dialog,
    exchanges_stats_dialog,
    exchanges_subscriptions_dialog,
    kpi_dialog,
    game_dialog,
    broadcast_dialog,
    groups_dialog,
    search_dialog,
    files_dialog,
]

__all__ = ["dialogs_list", "common_dialogs_list"]

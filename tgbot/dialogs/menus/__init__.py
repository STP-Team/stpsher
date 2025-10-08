"""Импорт всех диалогов и добавление их в dialogs_list."""

from tgbot.dialogs.menus.admin.main import admin_dialog
from tgbot.dialogs.menus.common.broadcast import broadcast_dialog
from tgbot.dialogs.menus.common.files import files_dialog
from tgbot.dialogs.menus.common.game.menu import game_dialog
from tgbot.dialogs.menus.common.groups import groups_dialog
from tgbot.dialogs.menus.common.kpi import kpi_dialog
from tgbot.dialogs.menus.common.schedule import schedules_dialog
from tgbot.dialogs.menus.common.search import search_dialog
from tgbot.dialogs.menus.gok.main import gok_dialog
from tgbot.dialogs.menus.head.main import head_dialog
from tgbot.dialogs.menus.mip.main import mip_dialog
from tgbot.dialogs.menus.root.main import root_dialog
from tgbot.dialogs.menus.user.main import user_dialog

dialogs_list = [
    user_dialog,
    head_dialog,
    admin_dialog,
    gok_dialog,
    mip_dialog,
    root_dialog,
]

common_dialogs_list = [
    schedules_dialog,
    kpi_dialog,
    game_dialog,
    broadcast_dialog,
    groups_dialog,
    search_dialog,
    files_dialog,
]

__all__ = [
    "dialogs_list",
    "common_dialogs_list",
]

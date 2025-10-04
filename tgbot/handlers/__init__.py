"""Import all routers and add them to routers_list."""
from tgbot.handlers.admin.main import admin_router
from tgbot.handlers.deep.group.settings import deeplink_group
from tgbot.handlers.gok.main import gok_router
from tgbot.handlers.group.admin.admin import group_admin_router
from tgbot.handlers.group.admin.settings import group_settings_router
from tgbot.handlers.group.cmds import group_cmds_router
from tgbot.handlers.group.group_join import chat_member
from tgbot.handlers.group.main import group_main_router
from tgbot.handlers.group.management import group_management_router
from tgbot.handlers.group.user.casino import group_casino_router
from tgbot.handlers.group.user.main import group_user_router
from tgbot.handlers.group.whois import whois_router
from tgbot.handlers.head.group.game.casino import head_game_casino_router
from tgbot.handlers.head.group.game.history import head_game_history_router
from tgbot.handlers.head.group.game.rating import head_group_game_rating_router
from tgbot.handlers.head.group.main import head_group_router
from tgbot.handlers.head.group.members import head_group_members_router
from tgbot.handlers.head.group.rating import head_group_rating_router
from tgbot.handlers.head.main import head_router
from tgbot.handlers.inline.inline import user_inline_router
from tgbot.handlers.mip.main import mip_router
from tgbot.handlers.root.main import root_router
from tgbot.handlers.user.auth.main import user_auth_router
from tgbot.handlers.user.game.casino import user_game_casino_router
from tgbot.handlers.user.main import user_router

routers_list = [
    deeplink_group,
    admin_router,
    root_router,
    gok_router,
    mip_router,
    head_router,
    head_game_history_router,
    head_group_game_rating_router,
    head_group_router,
    head_group_members_router,
    head_group_rating_router,
    head_game_casino_router,
    user_router,
    user_auth_router,
    user_game_casino_router,
    user_inline_router,
    group_main_router,
    group_cmds_router,
    group_management_router,
    whois_router,
    group_admin_router,
    group_user_router,
    group_casino_router,
    group_settings_router,
    chat_member,
]

__all__ = [
    "routers_list",
]

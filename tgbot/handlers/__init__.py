"""Импортируем все роутеры."""

from tgbot.handlers.auth import user_auth_router
from tgbot.handlers.channels.join import channels_router
from tgbot.handlers.cmds import cmds_router
from tgbot.handlers.deeplinks import deeplink_router
from tgbot.handlers.exchange_reschedule import exchange_reschedule_router
from tgbot.handlers.groups.admin.admin import group_admin_router
from tgbot.handlers.groups.admin.settings import group_settings_router
from tgbot.handlers.groups.join import groups_router
from tgbot.handlers.groups.user.casino import group_casino_router
from tgbot.handlers.groups.user.main import group_user_router
from tgbot.handlers.groups.user.whois import group_whois_router
from tgbot.handlers.inline.inline import user_inline_router
from tgbot.handlers.start import start_router

routers_list = [
    deeplink_router,
    cmds_router,
    start_router,
    user_auth_router,
    exchange_reschedule_router,
    user_inline_router,
    group_whois_router,
    group_admin_router,
    group_user_router,
    group_casino_router,
    group_settings_router,
    channels_router,
    groups_router,
]

__all__ = [
    "routers_list",
]

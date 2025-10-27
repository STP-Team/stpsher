"""Импортируем все роутеры."""

from tgbot.handlers.auth import user_auth_router
from tgbot.handlers.common.whois import whois_router
from tgbot.handlers.deeplinks import deeplink_router
from tgbot.handlers.group.admin.admin import group_admin_router
from tgbot.handlers.group.admin.settings import group_settings_router
from tgbot.handlers.group.group_join import chat_member
from tgbot.handlers.group.user.main import group_user_router
from tgbot.handlers.group.whois import group_whois_router
from tgbot.handlers.inline.inline import user_inline_router
from tgbot.handlers.start import start_router

routers_list = [
    deeplink_router,
    start_router,
    whois_router,
    user_auth_router,
    user_inline_router,
    group_whois_router,
    group_admin_router,
    group_user_router,
    group_settings_router,
    chat_member,
]

__all__ = [
    "routers_list",
]

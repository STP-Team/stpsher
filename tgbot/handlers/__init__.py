"""Import all routers and add them to routers_list."""

from tgbot.handlers.admin.main import admin_router
from tgbot.handlers.user.auth.main import user_auth_router
from tgbot.handlers.user.main import user_router
from tgbot.handlers.user.schedule.main import user_schedule_router

routers_list = [
    admin_router,
    user_router,
    user_auth_router,
    user_schedule_router,
]

__all__ = [
    "routers_list",
]

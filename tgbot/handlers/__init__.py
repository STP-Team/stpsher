"""Import all routers and add them to routers_list."""

from tgbot.handlers.admin.main import admin_router
from tgbot.handlers.gok.game.achievements import gok_game_achievements_router
from tgbot.handlers.gok.game.main import gok_game_router
from tgbot.handlers.gok.main import gok_router
from tgbot.handlers.group.casino import group_casino_router
from tgbot.handlers.group.whois import whois_router
from tgbot.handlers.head.kpi import head_kpi_router
from tgbot.handlers.head.main import head_router
from tgbot.handlers.head.schedule.group import head_schedule_group_router
from tgbot.handlers.mip.broadcast import mip_broadcast_router
from tgbot.handlers.mip.game.achievements import mip_game_achievements_router
from tgbot.handlers.mip.game.main import mip_game_router
from tgbot.handlers.mip.main import mip_router
from tgbot.handlers.mip.schedule.list import mip_list_router
from tgbot.handlers.mip.schedule.main import mip_schedule_router
from tgbot.handlers.mip.schedule.upload import mip_upload_router
from tgbot.handlers.mip.search import mip_search_router
from tgbot.handlers.user.auth.main import user_auth_router
from tgbot.handlers.user.game.achievements import user_game_achievements_router
from tgbot.handlers.user.game.casino import user_game_casino_router
from tgbot.handlers.user.game.history import user_game_history_router
from tgbot.handlers.user.game.inventory import user_game_inventory_router
from tgbot.handlers.user.game.main import user_game_router
from tgbot.handlers.user.game.shop import user_game_shop_router
from tgbot.handlers.user.inline import user_inline_router
from tgbot.handlers.user.kpi import user_kpi_router
from tgbot.handlers.user.links import user_links_router
from tgbot.handlers.user.main import user_router
from tgbot.handlers.user.schedule.duties import user_schedule_duty_router
from tgbot.handlers.user.schedule.group import user_schedule_group_router
from tgbot.handlers.user.schedule.heads import user_schedule_head_router
from tgbot.handlers.user.schedule.main import user_schedule_router
from tgbot.handlers.user.schedule.my import user_schedule_my_router

routers_list = [
    admin_router,
    gok_router,
    gok_game_router,
    gok_game_achievements_router,
    head_router,
    head_kpi_router,
    head_schedule_group_router,
    mip_router,
    mip_game_router,
    mip_game_achievements_router,
    mip_broadcast_router,
    mip_schedule_router,
    mip_upload_router,
    mip_list_router,
    mip_search_router,
    user_router,
    user_auth_router,
    user_schedule_router,
    user_schedule_my_router,
    user_schedule_duty_router,
    user_schedule_head_router,
    user_schedule_group_router,
    user_kpi_router,
    user_game_router,
    user_game_shop_router,
    user_game_inventory_router,
    user_game_achievements_router,
    user_game_casino_router,
    user_game_history_router,
    user_links_router,
    user_inline_router,
    whois_router,
    group_casino_router,
]

__all__ = [
    "routers_list",
]

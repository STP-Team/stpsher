"""Group handlers package."""

from .cmds import group_cmds_router
from .main import group_main_router
from .management import group_management_router

__all__ = [
    "group_main_router",
    "group_cmds_router",
    "group_management_router",
]

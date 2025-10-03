"""Генерация окон управления группами для специалистов."""

from tgbot.dialogs.menus.common.groups import create_groups_window
from tgbot.misc.states.dialogs.user import UserSG

(
    groups_window,
    groups_list_window,
    groups_list_detail_window,
    groups_cmds_window,
    groups_access_window,
    groups_service_messages_window,
    groups_members_window,
    groups_remove_bot_window,
) = create_groups_window(UserSG, UserSG.groups)

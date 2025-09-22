import logging

from aiogram import Router
from aiogram.filters import IS_ADMIN, IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated

from infrastructure.database.repo.STP.requests import MainRequestsRepo

logger = logging.getLogger(__name__)

chat_member = Router()

recent_bot_additions = {}
# Track groups where admin rights were granted to prevent member message
admin_granted_groups = set()


# Admin handlers first (higher priority)
@chat_member.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> IS_ADMIN)
)
async def bot_got_direct_admin_rights(
    event: ChatMemberUpdated, stp_repo: MainRequestsRepo
):
    """Handle when bot gets admin rights directly (startgroup link)."""
    if event.chat.type in ["group", "supergroup"]:
        # Mark that admin rights were granted
        admin_granted_groups.add(event.chat.id)

        # Add group to database
        existing_group = await stp_repo.group.get_group(event.chat.id)
        if not existing_group:
            group = await stp_repo.group.add_group(
                group_id=event.chat.id, invited_by=event.from_user.id
            )
            if group:
                logger.info(
                    f"[БД] Группа {event.chat.id} добавлена в базу данных пользователем {event.from_user.id}"
                )
            else:
                logger.error(
                    f"[БД] Ошибка добавления группы {event.chat.id} в базу данных"
                )
        else:
            logger.info(f"[БД] Группа {event.chat.id} уже существует в базе данных")

        # Send startgroup welcome message
        await event.answer("""<b>Спасибо за приглашение!</b>

Бот получил права администратора и готов к работе

Для проверки и изменения настроек группы используй команду /settings""")


@chat_member.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> IS_MEMBER)
)
async def bot_added_to_group(event: ChatMemberUpdated):
    """Handle when bot is added to a group as regular member."""
    if event.chat.type in ["group", "supergroup"]:
        import asyncio
        import time

        # Log for debugging
        logger.info(
            f"Bot added as member in {event.chat.id}: old_status={event.old_chat_member.status}, new_status={event.new_chat_member.status}"
        )

        # Check if admin rights were already granted (prevents duplicate messages)
        if event.chat.id in admin_granted_groups:
            admin_granted_groups.discard(event.chat.id)
            logger.info(
                f"Skipping member message for {event.chat.id} - admin rights already granted"
            )
            return

        # Track when bot was added to detect quick admin promotions
        recent_bot_additions[event.chat.id] = time.time()

        # Wait a bit to see if we get promoted to admin immediately (startgroup case)
        await asyncio.sleep(1)

        # Check if we're still just a member (not promoted to admin)
        if event.chat.id in recent_bot_additions:
            await event.answer("""<b>Спасибо за приглашение! 👋</b>

Чтобы эффективно использовать мои возможности, пожалуйста, назначь меня администратором""")


@chat_member.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_MEMBER >> IS_ADMIN)
)
async def bot_got_manual_admin_rights(
    event: ChatMemberUpdated, stp_repo: MainRequestsRepo
):
    """Handle when bot gets admin rights manually (promoted from member)."""
    if event.chat.type in ["group", "supergroup"]:
        # Log for debugging
        logger.info(
            f"Bot manually promoted to admin in {event.chat.id}: old_status={event.old_chat_member.status}, new_status={event.new_chat_member.status}"
        )

        # Clean up the tracking
        if event.chat.id in recent_bot_additions:
            del recent_bot_additions[event.chat.id]

        # Add group to database if not exists
        existing_group = await stp_repo.group.get_group(event.chat.id)
        if not existing_group:
            group = await stp_repo.group.add_group(
                group_id=event.chat.id, invited_by=event.from_user.id
            )
            if group:
                logger.info(
                    f"[БД] Группа {event.chat.id} добавлена в базу данных пользователем {event.from_user.id}"
                )
            else:
                logger.error(
                    f"[БД] Ошибка добавления группы {event.chat.id} в базу данных"
                )
        else:
            logger.info(f"[БД] Группа {event.chat.id} уже существует в базе данных")

        # Send manual promotion message
        await event.answer("""<b>Спасибо! 🙏🏻</b>

Права администратора успешно выданы, и бот готов к работе

Для проверки и изменения настроек группы используй команду /settings""")


@chat_member.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_ADMIN >> IS_MEMBER)
)
async def bot_lost_admin_rights(event: ChatMemberUpdated):
    """Handle when bot gets admin rights in a group."""
    if event.chat.type in ["group", "supergroup"]:
        await event.answer("""<b>Права администратора удалены 🥹</b>

Без наличия прав я не смогу корректно работать в группе""")


@chat_member.chat_member()
async def handle_chat_member_update(event: ChatMemberUpdated):
    """Handle when any user joins or leaves a group."""
    # This handler will be processed by the GroupsMiddleware
    # We just need to register it to ensure chat_member updates are captured
    pass

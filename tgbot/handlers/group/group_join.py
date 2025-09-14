import logging

from aiogram import Router
from aiogram.filters import IS_ADMIN, IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated

from infrastructure.database.repo.STP.requests import MainRequestsRepo

logger = logging.getLogger(__name__)

chat_member = Router()


@chat_member.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> IS_MEMBER)
)
async def bot_added_to_group(event: ChatMemberUpdated):
    """Handle when bot is added to a group."""
    if event.chat.type in ["group", "supergroup"]:
        await event.answer("""<b>Привет 👋</b>

Для корректной работы мне необходимо выдать права администратора

Для выдачи прав:
1. Открой настройки группы
2. Найди бота в списке участников
3. Выдай стандартные права администратора""")


@chat_member.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_MEMBER >> IS_ADMIN)
)
async def bot_got_admin_rights(event: ChatMemberUpdated, stp_repo: MainRequestsRepo):
    """Handle when bot gets admin rights in a group."""
    if event.chat.type in ["group", "supergroup"]:
        # Проверяем, существует ли уже группа в БД
        existing_group = await stp_repo.group.get_group(event.chat.id)

        if not existing_group:
            # Добавляем группу в БД
            group = await stp_repo.group.add_group(
                group_id=event.chat.id,
                invited_by=event.from_user.id
            )

            if group:
                logger.info(f"[БД] Группа {event.chat.id} добавлена в базу данных пользователем {event.from_user.id}")
            else:
                logger.error(f"[БД] Ошибка добавления группы {event.chat.id} в базу данных")
        else:
            logger.info(f"[БД] Группа {event.chat.id} уже существует в базе данных")

        await event.answer("""<b>Спасибо 🙏🏻</b>

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

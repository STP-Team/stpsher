import logging

from aiogram import Router
from aiogram.filters import IS_ADMIN, IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated
from stp_database import MainRequestsRepo

logger = logging.getLogger(__name__)


groups_router = Router()


@groups_router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> IS_MEMBER)
)
async def bot_added_to_group(event: ChatMemberUpdated) -> None:
    """Обработчик добавления бота в группу.

    Args:
        event: Callback query от Telegram
    """
    await event.answer("""<b>Спасибо за приглашение! 👋</b>

Чтобы эффективно использовать мои возможности, пожалуйста, назначь меня администратором""")


@groups_router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> IS_ADMIN)
)
async def got_auto_admin_rights(
    event: ChatMemberUpdated, stp_repo: MainRequestsRepo
) -> None:
    """Обработчик автоматического получения прав администратора для бота через startgroup.

    Args:
        event: Callback query от Telegram
        stp_repo: Репозиторий базы данных
    """
    group = await stp_repo.group.get_groups(event.chat.id)

    if not group:
        group = await stp_repo.group.add_group(
            group_id=event.chat.id, invited_by=event.from_user.id
        )
        if group:
            logger.info(
                f"[БД] Группа {event.chat.id} добавлена в базу данных пользователем {event.from_user.id}"
            )
        else:
            logger.error(f"[БД] Ошибка добавления группы {event.chat.id} в базу данных")
    else:
        logger.info(f"[БД] Группа {event.chat.id} уже существует в базе данных")

    await event.answer("""<b>Спасибо за приглашение!</b>

Бот получил права администратора и готов к работе

Для проверки и изменения настроек группы используй команду /settings""")


@groups_router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_MEMBER >> IS_ADMIN)
)
async def got_manual_admin_rights(event: ChatMemberUpdated, stp_repo: MainRequestsRepo):
    """Обработчик ручного получения прав администратора для бота.

    Args:
        event: Callback query от Telegram
        stp_repo: Репозиторий базы данных
    """
    group = await stp_repo.group.get_groups(event.chat.id)

    if not group:
        group = await stp_repo.group.add_group(
            group_id=event.chat.id, invited_by=event.from_user.id
        )
        if group:
            logger.info(
                f"[БД] Группа {event.chat.id} добавлена в базу данных пользователем {event.from_user.id}"
            )
        else:
            logger.error(f"[БД] Ошибка добавления группы {event.chat.id} в базу данных")
    else:
        logger.info(f"[БД] Группа {event.chat.id} уже существует в базе данных")

    await event.answer("""<b>Спасибо! 🙏🏻</b>

Права администратора успешно выданы, и бот готов к работе

Для проверки и изменения настроек группы используй команду /settings""")


@groups_router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_ADMIN >> IS_MEMBER)
)
async def bot_lost_admin_rights(event: ChatMemberUpdated) -> None:
    """Обработчик потери прав администратора.

    Args:
        event: Callback query от Telegram
    """
    await event.answer("""🥹 <b>Права удалены</b>

Без наличия прав я не смогу корректно работать в группе

<i>Я сохранил настройки группы на случай, если ты захочешь вернуть мне права</i>""")


@groups_router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_ADMIN >> IS_NOT_MEMBER)
)
async def bot_get_kicked(event: ChatMemberUpdated, stp_repo: MainRequestsRepo) -> None:
    """Обработчик исключения бота из группы.

    Args:
        event: Callback query от Telegram
        stp_repo: Репозиторий операций с базой STP
    """
    await event.bot.send_message(
        chat_id=event.from_user.id,
        text="""🔥 <b>Бот удален из группы</b>
        
Настройки группы сброшены до стандартных

<i>При добавлении бота обратно нужно будет настроить ее обратно</i>""",
    )
    await stp_repo.group.delete_group(event.chat.id)


@groups_router.chat_member()
async def handle_chat_member_update(event: ChatMemberUpdated):
    """Handle when any user joins or leaves a groups."""
    # This handler will be processed by the GroupsMiddleware
    # We just need to register it to ensure chat_member updates are captured
    pass

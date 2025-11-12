import logging

from aiogram import F, Router
from aiogram.filters import IS_ADMIN, IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter
from aiogram.types import (
    ChatJoinRequest,
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from stp_database import Employee, MainRequestsRepo

logger = logging.getLogger(__name__)

channels_router = Router()
channels_router.my_chat_member.filter(F.chat.type == "channel")


@channels_router.chat_join_request()
async def channel_join_request(
    request: ChatJoinRequest, user: Employee, stp_repo: MainRequestsRepo
):
    """Handle new channel join requests"""
    chat = request.chat

    channel = await stp_repo.group.get_groups(chat.id)

    if channel.remove_unemployed:
        if not user:
            await request.decline()
            await request.answer_pm(
                text=f"✋ Запрос на вступление в канал <b>{chat.title}</b> отклонен\n\nДоступ к каналу разрешен только сотрудникам"
            )
    else:
        await request.approve()

        channel_link = f"t.me/c/{str(chat.id).replace('-100', '')}"
        await request.answer_pm(
            text=f"👌 Запрос на вступление в канал <b>{chat.title}</b> принят",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="👀 Открыть канал", url=channel_link)]
                ]
            ),
        )


@channels_router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> IS_ADMIN)
)
async def got_auto_admin_rights_channel(
    event: ChatMemberUpdated, stp_repo: MainRequestsRepo
) -> None:
    """Обработчик автоматического получения прав администратора для бота в канале.

    Args:
        event: Событие изменения статуса участника чата от Telegram
        stp_repo: Репозиторий базы данных
    """
    channel = await stp_repo.group.get_groups(event.chat.id)

    if not channel:
        channel = await stp_repo.group.add_group(
            group_id=event.chat.id, invited_by=event.from_user.id
        )
        if channel:
            logger.info(
                f"[БД] Канал {event.chat.id} добавлен в базу данных пользователем {event.from_user.id}"
            )
        else:
            logger.error(f"[БД] Ошибка добавления канала {event.chat.id} в базу данных")
    else:
        logger.info(f"[БД] Канал {event.chat.id} уже существует в базе данных")

    await event.answer("""<b>Спасибо за добавление!</b>

Бот получил права администратора и готов к работе

Для проверки и изменения настроек канала используй раздел <b>👯‍♀️ Группы</b>""")


@channels_router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_MEMBER >> IS_ADMIN)
)
async def got_manual_admin_rights_channel(
    event: ChatMemberUpdated, stp_repo: MainRequestsRepo
):
    """Обработчик ручного получения прав администратора для бота в канале.

    Args:
        event: Событие изменения статуса участника чата от Telegram
        stp_repo: Репозиторий базы данных
    """
    channel = await stp_repo.group.get_groups(event.chat.id)

    if not channel:
        channel = await stp_repo.group.add_group(
            group_id=event.chat.id, invited_by=event.from_user.id
        )
        if channel:
            logger.info(
                f"[БД] Канал {event.chat.id} добавлен в базу данных пользователем {event.from_user.id}"
            )
        else:
            logger.error(f"[БД] Ошибка добавления канала {event.chat.id} в базу данных")
    else:
        logger.info(f"[БД] Канал {event.chat.id} уже существует в базе данных")

    await event.bot.send_message(
        event.from_user.id,
        """<b>Спасибо! 🙏🏻</b>

Права администратора успешно выданы, и бот готов к работе

Для проверки и изменения настроек канала используй раздел <b>👯‍♀️ Группы</b>""",
    )


@channels_router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_ADMIN >> IS_MEMBER)
)
async def bot_lost_admin_rights_channel(event: ChatMemberUpdated) -> None:
    """Обработчик потери прав администратора в канале.

    Args:
        event: Событие изменения статуса участника чата от Telegram
    """
    await event.answer("""🥹 <b>Права удалены</b>

Без наличия прав я не смогу корректно работать в канале

<i>Я сохранил настройки канала на случай, если ты захочешь вернуть мне права</i>""")


@channels_router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_ADMIN >> IS_NOT_MEMBER)
)
async def bot_get_kicked_from_channel(
    event: ChatMemberUpdated, stp_repo: MainRequestsRepo
) -> None:
    """Обработчик исключения бота из канала.

    Args:
        event: Событие изменения статуса участника чата от Telegram
        stp_repo: Репозиторий операций с базой STP
    """
    await event.bot.send_message(
        chat_id=event.from_user.id,
        text=f"""🔥 <b>Бот удален из канала</b> <code>{event.chat.title}</code>

Настройки канала сброшены до стандартных

<i>При добавлении бота обратно нужно будет настроить его обратно</i>""",
    )
    await stp_repo.group.delete_group(event.chat.id)

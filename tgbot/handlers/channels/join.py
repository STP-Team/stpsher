import logging

from aiogram import F, Router
from aiogram.filters import IS_ADMIN, IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter
from aiogram.types import (
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.utils.deep_linking import create_start_link
from stp_database import MainRequestsRepo

logger = logging.getLogger(__name__)

channels_router = Router()
channels_router.my_chat_member.filter(F.chat.type == "channel")


@channels_router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> IS_ADMIN)
)
async def got_auto_admin_rights_channel(
    event: ChatMemberUpdated, stp_repo: MainRequestsRepo
) -> None:
    """Обработчик автоматического получения прав администратора для бота в канале.

    Args:
        event: Событие изменения статуса участника чата от Telegram
        stp_repo: Репозиторий операций с базой STP
    """
    channel = await stp_repo.group.get_groups(event.chat.id)

    if not channel:
        channel = await stp_repo.group.add_group(
            group_id=event.chat.id, group_type="channel", invited_by=event.from_user.id
        )
        # Добавляем участника, игнорируя дублирующие записи
        try:
            await stp_repo.group_member.add_member(event.chat.id, event.from_user.id)
        except Exception:
            pass
        if channel:
            logger.info(
                f"[БД] Канал {event.chat.id} добавлен в базу данных пользователем {event.from_user.id}"
            )
        else:
            logger.error(f"[БД] Ошибка добавления канала {event.chat.id} в базу данных")
    else:
        logger.info(f"[БД] Канал {event.chat.id} уже существует в базе данных")

    settings_deeplink = await create_start_link(
        event.bot, payload=f"group_{channel.group_id}", encode=True
    )
    channel_link = f"t.me/c/{str(event.chat.id).replace('-100', '')}"

    await event.bot.send_message(
        event.from_user.id,
        """👋 <b>Спасибо за приглашение!</b>

Бот получил права администратора и готов к работе

Для проверки и изменения настроек канала используй раздел <b>👯‍♀️ Группы</b>""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="👀 Открыть канал", url=channel_link)],
                [
                    InlineKeyboardButton(
                        text="⚙️ Настройки канала", url=settings_deeplink
                    )
                ],
            ]
        ),
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

Настройки канала сброшены до стандартных, сохраненные участники удалены из базы

<i>При добавлении бота обратно нужно будет настроить его обратно</i>""",
    )
    await stp_repo.group.delete_group(event.chat.id)
    await stp_repo.group_member.remove_all_members(event.chat.id)

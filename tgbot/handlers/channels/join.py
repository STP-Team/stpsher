import logging

from aiogram import F, Router
from aiogram.filters import IS_ADMIN, IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter
from aiogram.types import (
    ChatJoinRequest,
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.utils.deep_linking import create_start_link
from stp_database import Employee, MainRequestsRepo

logger = logging.getLogger(__name__)

channels_router = Router()
channels_router.my_chat_member.filter(F.chat.type == "channel")


@channels_router.chat_join_request()
async def channel_join_request(
    request: ChatJoinRequest, user: Employee, stp_repo: MainRequestsRepo
) -> None:
    """Обработчик новых запросов на вход в канал.

    Args:
        request: Запрос входа
        user: Экземпляр пользователя с моделью Employee
        stp_repo: Репозиторий операций с базой STP
    """
    try:
        chat = request.chat

        # Получаем настройки канала из БД
        channel = await stp_repo.group.get_groups(chat.id)

        # Проверяем, что канал существует в БД
        if not channel:
            logger.warning(f"Канал {chat.id} не найден в базе данных")
            await request.decline()
            return

        channel_link = f"t.me/c/{str(chat.id).replace('-100', '')}"

        # Проверка на удаление уволенных
        if channel.remove_unemployed:
            if not user:
                await request.decline()
                await stp_repo.group_member.remove_member(chat.id, request.from_user.id)
                await request.answer_pm(
                    text=f"✋ Запрос на вступление в канал <b>{chat.title}</b> отклонен\n\nДоступ к каналу разрешен только сотрудникам"
                )
                return
            # Если пользователь есть и remove_unemployed=True, проверяем роли дальше

        # Проверка ролей
        if channel.allowed_roles:
            if user and user.role in channel.allowed_roles:
                await request.approve()
                await stp_repo.group_member.add_member(chat.id, request.from_user.id)
                await request.answer_pm(
                    text=f"👌 Запрос на вступление в канал <b>{chat.title}</b> принят",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="👀 Открыть канал", url=channel_link
                                )
                            ]
                        ]
                    ),
                )
            else:
                await request.decline()
                await stp_repo.group_member.remove_member(chat.id, request.from_user.id)
                await request.answer_pm(
                    text=f"✋ Запрос на вступление в канал <b>{chat.title}</b> отклонен\n\nДоступ к каналу с твоим уровнем доступа запрещен"
                )
        else:
            # Нет ограничений по ролям - одобряем всех (кроме уже отфильтрованных безработных)
            await request.approve()
            await stp_repo.group_member.add_member(chat.id, request.from_user.id)
            await request.answer_pm(
                text=f"👌 Запрос на вступление в канал <b>{chat.title}</b> принят",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="👀 Открыть канал", url=channel_link
                            )
                        ]
                    ]
                ),
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке запроса входа в канал {chat.id}: {e}")
        try:
            await request.decline()
            await stp_repo.group_member.remove_member(chat.id, request.from_user.id)
        except Exception as decline_error:
            logger.error(f"Ошибка при отклонении запроса: {decline_error}")


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
            group_id=event.chat.id, group_type="channel", invited_by=event.from_user.id
        )
        await stp_repo.group_member.add_member(event.chat.id, event.from_user.id)
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

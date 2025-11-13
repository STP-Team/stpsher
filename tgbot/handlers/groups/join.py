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


groups_router = Router()
groups_router.my_chat_member.filter(F.chat.type.in_({"group", "supergroup"}))


@groups_router.chat_join_request()
async def join_request(
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
        group = await stp_repo.group.get_groups(chat.id)

        # Проверяем, что канал существует в БД
        if not group:
            logger.warning(f"Группа {chat.id} не найдена в базе данных")
            await request.decline()
            return

        # Проверяем настройку auto_apply - если отключена, пропускаем запрос
        if not group.auto_apply:
            return

        channel_link = f"t.me/c/{str(chat.id).replace('-100', '')}"

        # Проверка на удаление уволенных
        if group.remove_unemployed:
            if not user:
                await request.decline()
                await stp_repo.group_member.remove_member(chat.id, request.from_user.id)
                await request.answer_pm(
                    text=f"✋ Запрос на вступление в {'группу' if group.group_type == 'group' else 'канал'} <b>{chat.title}</b> отклонен\n\nДоступ разрешен только сотрудникам"
                )
                return
            # Если пользователь есть и remove_unemployed=True, проверяем роли дальше

        # Проверка ролей
        if group.allowed_roles:
            if user and user.role in group.allowed_roles:
                await request.approve()
                await stp_repo.group_member.add_member(chat.id, request.from_user.id)
                await request.answer_pm(
                    text=f"👌 Запрос на вступление в {'группу' if group.group_type == 'group' else 'канал'} <b>{chat.title}</b> принят",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text=f"👀 Открыть {'группу' if group.group_type == 'group' else 'канал'}",
                                    url=channel_link,
                                )
                            ]
                        ]
                    ),
                )
            else:
                await request.decline()
                await stp_repo.group_member.remove_member(chat.id, request.from_user.id)
                await request.answer_pm(
                    text=f"✋ Запрос на вступление в {'группу' if group.group_type == 'group' else 'канал'} <b>{chat.title}</b> отклонен\n\nДоступ с твоим уровнем доступа запрещен"
                )
        else:
            # Нет ограничений по ролям - одобряем всех (кроме уже отфильтрованных безработных)
            await request.approve()
            await stp_repo.group_member.add_member(chat.id, request.from_user.id)
            await request.answer_pm(
                text=f"👌 Запрос на вступление в {'группу' if group.group_type == 'group' else 'канал'} <b>{chat.title}</b> принят",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=f"👀 Открыть {'группу' if group.group_type == 'group' else 'канал'}",
                                url=channel_link,
                            )
                        ]
                    ]
                ),
            )

    except Exception as e:
        chat_id = request.chat.id if request.chat else "unknown"
        logger.error(f"Ошибка при обработке запроса входа в канал {chat_id}: {e}")
        try:
            await request.decline()
            if request.chat:
                await stp_repo.group_member.remove_member(
                    request.chat.id, request.from_user.id
                )
        except Exception as decline_error:
            error_str = str(decline_error)
            # Не логируем ошибки, когда запрос уже недоступен
            if "HIDE_REQUESTER_MISSING" not in error_str:
                logger.error(f"Ошибка при отклонении запроса: {decline_error}")
            else:
                logger.debug(
                    f"Запрос на вступление уже недоступен для пользователя {request.from_user.id if request.from_user else 'unknown'}"
                )


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
            group_id=event.chat.id, group_type="group", invited_by=event.from_user.id
        )
        if group:
            logger.info(
                f"[БД] Группа {event.chat.id} добавлена в базу данных пользователем {event.from_user.id}"
            )
        else:
            logger.error(f"[БД] Ошибка добавления группы {event.chat.id} в базу данных")
    else:
        logger.info(f"[БД] Группа {event.chat.id} уже существует в базе данных")

    await event.answer("""👋 <b>Спасибо за приглашение!</b>

Бот получил права администратора и готов к работе

Для проверки и изменения настроек группы используй раздел <b>👯‍♀️ Группы</b>""")


@groups_router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> IS_MEMBER)
)
async def bot_added_to_group(event: ChatMemberUpdated) -> None:
    """Обработчик добавления бота в группу.

    Args:
        event: Callback query от Telegram
    """
    await event.answer("""👋 <b>Спасибо за приглашение!</b>

Чтобы эффективно использовать мои возможности, пожалуйста, назначь меня администратором""")


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
            group_id=event.chat.id, group_type="group", invited_by=event.from_user.id
        )
        if group:
            logger.info(
                f"[БД] Группа {event.chat.id} добавлена в базу данных пользователем {event.from_user.id}"
            )
        else:
            logger.error(f"[БД] Ошибка добавления группы {event.chat.id} в базу данных")
    else:
        logger.info(f"[БД] Группа {event.chat.id} уже существует в базе данных")

    await event.answer("""🙏🏻 <b>Спасибо!</b>

Права администратора успешно выданы, и бот готов к работе

Для проверки и изменения настроек группы используй раздел <b>👯‍♀️ Группы</b>""")


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
        text=f"""🔥 <b>Бот удален из группы</b> {event.chat.title}
        
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

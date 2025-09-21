import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, ChatMemberUpdated, InlineQuery, Message

from infrastructure.database.repo.STP.requests import MainRequestsRepo

logger = logging.getLogger(__name__)


class GroupsMiddleware(BaseMiddleware):
    """
    Middleware responsible for groups access control logic
    """

    async def __call__(
        self,
        handler: Callable[
            [
                Union[Message, CallbackQuery, InlineQuery, ChatMemberUpdated],
                Dict[str, Any],
            ],
            Awaitable[Any],
        ],
        event: Union[Message, CallbackQuery, InlineQuery, ChatMemberUpdated],
        data: Dict[str, Any],
    ) -> Any:
        # Get repo from previous middleware (UsersMiddleware)
        stp_repo: MainRequestsRepo = data.get("stp_repo")

        # Handle different event types
        if isinstance(event, Message) and event.chat.type in ["group", "supergroup"]:
            await self._update_group(event, stp_repo)
        elif isinstance(event, ChatMemberUpdated) and event.chat.type in [
            "group",
            "supergroup",
        ]:
            await self._handle_group_membership_change(event, stp_repo)

        # Continue to the next middleware/handler
        result = await handler(event, data)
        return result

    @staticmethod
    async def _update_group(
        event: Message,
        stp_repo: MainRequestsRepo,
    ):
        """
        Обновление участников группы при отправке сообщений в группе
        Проверяет, если сообщение отправлено в группе из таблицы groups,
        и добавляет пользователя в group_members если его там нет.
        Также проверяет настройки группы и банит неактивных сотрудников.
        :param event: Сообщение от пользователя
        :param stp_repo: Репозиторий для работы с БД
        """
        if not event.from_user:
            return

        group_id = event.chat.id
        user_id = event.from_user.id

        # Добавляем отладочное логирование
        logger.debug(
            f"[Группы] Обработка сообщения от пользователя {user_id} в группе {group_id}: '{event.text or 'не текст'}'"
        )

        try:
            # Проверяем, есть ли группа в таблице groups
            group = await stp_repo.group.get_group(group_id)
            if not group:
                return

            # Проверяем настройку remove_unemployed для группы
            if group.remove_unemployed:
                # Получаем ID бота, чтобы не банить самого себя
                bot_id = event.bot.id

                # Не проверяем бота
                if user_id == bot_id:
                    return

                # Проверяем, является ли пользователь активным сотрудником
                employee = await stp_repo.employee.get_user(user_id=user_id)

                if not employee:
                    # Пользователь не найден в таблице employees - банить
                    await GroupsMiddleware._ban_user_from_group(
                        event, user_id, group_id, stp_repo
                    )
                    logger.info(
                        f"[Группы] Пользователь {user_id} забанен в группе {group_id} (не найден в employees)"
                    )
                    return

            # Проверяем, является ли пользователь уже участником
            is_member = await stp_repo.group_member.is_member(group_id, user_id)
            if is_member:
                return

            # Добавляем пользователя в участники группы
            result = await stp_repo.group_member.add_member(group_id, user_id)
            if result:
                logger.info(f"[Группы] Добавлен участник {user_id} в группу {group_id}")
            else:
                logger.warning(
                    f"[Группы] Не удалось добавить участника {user_id} в группу {group_id}"
                )

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка обновления участников группы {group_id} для пользователя {user_id}: {e}"
            )

    @staticmethod
    async def _ban_user_from_group(
        event: Message, user_id: int, group_id: int, stp_repo: MainRequestsRepo
    ):
        """
        Банит пользователя в группе и удаляет его из group_members
        :param event: Сообщение от пользователя
        :param user_id: ID пользователя для бана
        :param group_id: ID группы
        :param stp_repo: Репозиторий для работы с БД
        """
        # Получаем информацию о пользователе
        user_mention = (
            f"@{event.from_user.username}"
            if event.from_user.username
            else f"#{user_id}"
        )
        user_fullname = f"{event.from_user.first_name or ''} {event.from_user.last_name or ''}".strip()

        await GroupsMiddleware._execute_ban(
            bot=event.bot,
            user_id=user_id,
            group_id=group_id,
            stp_repo=stp_repo,
            user_mention=user_mention,
            user_fullname=user_fullname,
            reason_text="был заблокирован в данной группе",
        )

    @staticmethod
    async def _handle_group_membership_change(
        event: ChatMemberUpdated,
        stp_repo: MainRequestsRepo,
    ):
        """
        Обработка изменений участников группы
        Обрабатывает события добавления/удаления пользователей в группу
        :param event: Событие изменения статуса участника
        :param stp_repo: Репозиторий для работы с БД
        """
        if not event.new_chat_member or not event.new_chat_member.user:
            return

        group_id = event.chat.id
        user_id = event.new_chat_member.user.id
        bot_id = event.bot.id

        # Не обрабатываем изменения статуса бота
        if user_id == bot_id:
            return

        try:
            # Проверяем, есть ли группа в таблице groups
            group = await stp_repo.group.get_group(group_id)
            if not group:
                return

            old_status = (
                event.old_chat_member.status if event.old_chat_member else "left"
            )
            new_status = event.new_chat_member.status

            # Логируем изменения статуса для отладки
            logger.info(
                f"[Группы] Изменение статуса пользователя {user_id} в группе {group_id}: {old_status} -> {new_status}"
            )

            # Пользователь добавлен в группу (стал участником или администратором)
            if old_status in ["left", "kicked"] and new_status in [
                "member",
                "administrator",
                "creator",
            ]:
                logger.info(
                    f"[Группы] Обработка добавления пользователя {user_id} в группу {group_id}"
                )
                await GroupsMiddleware._handle_user_added_to_group(
                    event, group_id, user_id, group, stp_repo
                )

            # Пользователь удален из группы (покинул или был исключен)
            elif old_status in [
                "member",
                "administrator",
                "creator",
            ] and new_status in ["left", "kicked"]:
                logger.info(
                    f"[Группы] Обработка удаления пользователя {user_id} из группы {group_id}"
                )
                await GroupsMiddleware._handle_user_removed_from_group(
                    group_id, user_id, stp_repo, new_status == "kicked"
                )
            else:
                logger.info(
                    f"[Группы] Неизвестное изменение статуса для пользователя {user_id} в группе {group_id}: {old_status} -> {new_status}"
                )

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка обработки изменения участника {user_id} в группе {group_id}: {e}"
            )

    @staticmethod
    async def _handle_user_added_to_group(
        event: ChatMemberUpdated,
        group_id: int,
        user_id: int,
        group,
        stp_repo: MainRequestsRepo,
    ):
        """
        Обработка добавления пользователя в группу
        """
        try:
            # Проверяем настройку remove_unemployed для группы
            if group.remove_unemployed:
                # Проверяем, является ли пользователь активным сотрудником
                employee = await stp_repo.employee.get_user(user_id=user_id)

                if not employee:
                    # Пользователь не найден в таблице employees - банить
                    await GroupsMiddleware._ban_user_from_group_by_update(
                        event, user_id, group_id, stp_repo
                    )
                    logger.info(
                        f"[Группы] Пользователь {user_id} забанен при добавлении в группу {group_id} (не найден в employees)"
                    )
                    return

            # Добавляем пользователя в участники группы
            is_member = await stp_repo.group_member.is_member(group_id, user_id)
            if not is_member:
                result = await stp_repo.group_member.add_member(group_id, user_id)
                if result:
                    logger.info(
                        f"[Группы] Пользователь {user_id} добавлен в участники группы {group_id}"
                    )
                else:
                    logger.warning(
                        f"[Группы] Не удалось добавить пользователя {user_id} в участники группы {group_id}"
                    )

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка при добавлении пользователя {user_id} в группу {group_id}: {e}"
            )

    @staticmethod
    async def _handle_user_removed_from_group(
        group_id: int,
        user_id: int,
        stp_repo: MainRequestsRepo,
        was_kicked: bool = False,
    ):
        """
        Обработка удаления пользователя из группы
        """
        try:
            # Удаляем пользователя из таблицы group_members
            result = await stp_repo.group_member.remove_member(group_id, user_id)

            action = "исключен" if was_kicked else "покинул группу"
            if result:
                logger.info(
                    f"[Группы] Пользователь {user_id} {action} и удален из участников группы {group_id}"
                )
            else:
                logger.warning(
                    f"[Группы] Пользователь {user_id} {action}, но не удалось удалить из участников группы {group_id}"
                )

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка при удалении пользователя {user_id} из группы {group_id}: {e}"
            )

    @staticmethod
    async def _ban_user_from_group_by_update(
        event: ChatMemberUpdated,
        user_id: int,
        group_id: int,
        stp_repo: MainRequestsRepo,
    ):
        """
        Банит пользователя в группе при обработке ChatMemberUpdated событий
        :param event: Событие изменения участника
        :param user_id: ID пользователя для бана
        :param group_id: ID группы
        :param stp_repo: Репозиторий для работы с БД
        """
        # Получаем информацию о пользователе
        user = event.new_chat_member.user
        user_mention = f"@{user.username}" if user.username else f"#{user_id}"
        user_fullname = f"{user.first_name or ''} {user.last_name or ''}".strip()

        await GroupsMiddleware._execute_ban(
            bot=event.bot,
            user_id=user_id,
            group_id=group_id,
            stp_repo=stp_repo,
            user_mention=user_mention,
            user_fullname=user_fullname,
            reason_text="был заблокирован при попытке присоединения к группе",
        )

    @staticmethod
    async def _execute_ban(
        bot,
        user_id: int,
        group_id: int,
        stp_repo: MainRequestsRepo,
        user_mention: str,
        user_fullname: str,
        reason_text: str,
    ):
        """
        Общий метод для выполнения бана пользователя
        """
        try:
            # Формируем информацию о пользователе для уведомления
            if user_fullname:
                user_info = f"{user_fullname} ({user_mention})"
            else:
                user_info = user_mention

            # Банить пользователя в Telegram группе
            await bot.ban_chat_member(chat_id=group_id, user_id=user_id)

            # Удаляем пользователя из таблицы group_members
            await stp_repo.group_member.remove_member(group_id, user_id)

            # Отправляем уведомление в группу
            notification_text = (
                f"🚫 <b>Пользователь заблокирован</b>\n\n"
                f"Пользователь {user_info} {reason_text}\n"
                f"<i>Причина: пользователь не найден в базе данных сотрудников</i>"
            )

            await bot.send_message(
                chat_id=group_id, text=notification_text, parse_mode="HTML"
            )

            logger.info(
                f"[Группы] Пользователь {user_id} забанен и удален из группы {group_id}"
            )

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка при бане пользователя {user_id} из группы {group_id}: {e}"
            )

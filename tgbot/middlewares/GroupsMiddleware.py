"""Middleware для операций с группами."""

import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import CallbackQuery, ChatMemberUpdated, InlineQuery, Message
from stp_database import MainRequestsRepo
from stp_database.models.STP.group import Group

from tgbot.misc.helpers import format_fullname

logger = logging.getLogger(__name__)


class GroupsMiddleware(BaseMiddleware):
    """Middleware, отвечающий за функционал групп.

    Проверяет наличие доступа к группе, баны и прочие функции
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
        # Получаем репозиторий для работы с базой STP
        stp_repo: MainRequestsRepo = data.get("stp_repo")

        # Обрабатываем разные типы событий
        if isinstance(event, Message) and event.chat.type in ["group", "supergroup"]:
            # Проверяем является ли сообщение командой в незарегистрированной группе
            command_handled = await self._handle_unregistered_group_command(
                event, stp_repo
            )
            if command_handled:
                return None  # Не проверяем сообщение если команда в незарегистрированной группе

            # Проверяем и удаляем сервисные сообщения
            should_delete = await self._check_and_delete_service_message(
                event, stp_repo
            )
            if should_delete:
                return None  # Не проверяем сообщение если оно должно быть удалено

            await self._update_group(event, stp_repo)
        elif isinstance(event, ChatMemberUpdated) and event.chat.type in [
            "group",
            "supergroup",
        ]:
            await self._handle_group_membership_change(event, stp_repo)

        # Продолжаем к следующему middleware/обработчику
        result = await handler(event, data)
        return result

    @staticmethod
    async def _cleanup_removed_group(
        group_id: int,
        stp_repo: MainRequestsRepo,
    ):
        """Удаляет группу и всех её участников из базы когда бот был исключен из группы.

        Args:
            group_id: Идентификатор группы Telegram для удаления
            stp_repo: Репозиторий операций с базой STP
        """
        try:
            # Удаляем всех участников группы
            await stp_repo.group_member.remove_all_members(group_id)
            logger.info(f"[Группы] Удалены все участники группы {group_id}")

            # Удаляем саму группу
            await stp_repo.group.delete_group(group_id)
            logger.info(f"[Группы] Группа {group_id} удалена из базы")

        except Exception as e:
            logger.error(f"[Группы] Ошибка при очистке данных группы {group_id}: {e}")

    @staticmethod
    async def _update_group(
        event: Message,
        stp_repo: MainRequestsRepo,
    ):
        """Обновление участников группы при отправке сообщений в группе.

        Проверяет, если сообщение отправлено в группе из таблицы groups,
        и добавляет пользователя в group_members если его там нет.
        Также проверяет настройки группы и банит неактивных сотрудников.

        Args:
            event: Сообщение от пользователя
            stp_repo: Репозиторий операций с базой STP
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
            group = await stp_repo.group.get_groups(group_id)
            if not group:
                return

            # Не проверяем ботов
            if event.from_user.is_bot:
                return

            # Используем централизованную проверку на трудоустройство
            is_valid = await GroupsMiddleware._validate_user_employment(
                user_id, group_id, group, stp_repo, event.from_user
            )

            if not is_valid:
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
        """Банит пользователя в группе и удаляет его из group_members.

        Args:
            event: Сообщение от пользователя
            user_id: Идентификатор пользователя Telegram для бана
            group_id: Идентификатор группы Telegram
            stp_repo: Репозиторий операций с базой STP
        """
        await GroupsMiddleware._execute_ban(
            bot=event.bot,
            user_id=user_id,
            group_id=group_id,
            stp_repo=stp_repo,
            reason_text="был заблокирован в данной группе",
        )

    @staticmethod
    async def _handle_group_membership_change(
        event: ChatMemberUpdated,
        stp_repo: MainRequestsRepo,
    ):
        """Обработка изменений участников группы.

        Обрабатывает события добавления/удаления пользователей в группу

        Args:
            event: Событие изменения статуса участника
            stp_repo: Репозиторий операций с базой STP
        """
        # Инициализируем переменные для обработки ошибок
        group_id = None
        user_id = None

        try:
            # Проверяем корректность события
            if not event.new_chat_member or not event.new_chat_member.user:
                logger.warning(
                    "[Группы] Получено некорректное событие изменения участника"
                )
                return

            group_id = event.chat.id
            user_id = event.new_chat_member.user.id

            # Не обрабатываем изменения статуса ботов
            if event.new_chat_member.user.is_bot:
                return

            # Проверяем, что группа зарегистрирована в системе
            group = await stp_repo.group.get_groups(group_id)
            if not group:
                logger.debug(
                    f"[Группы] Группа {group_id} не зарегистрирована в системе"
                )
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
        """Обработка добавления пользователя в группу.

        Args:
            event: Событие добавления нового пользователя
            group_id: Идентификатор группы Telegram
            user_id: Идентификатор пользователя Telegram
            group: Экземпляр группы
            stp_repo: Репозиторий операций с базой STP
        """
        try:
            # Игнорируем ботов
            if event.new_chat_member.user.is_bot:
                logger.debug(
                    f"[Группы] Пользователь {user_id} определен как бот, игнорируем обработку"
                )
                return
            # Используем централизованную проверку на трудоустройство
            is_valid = await GroupsMiddleware._validate_user_employment(
                user_id, group_id, group, stp_repo, event.new_chat_member.user
            )

            if not is_valid:
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

                    # Отправляем уведомление о новом участнике, если включена настройка
                    if group.new_user_notify:
                        await GroupsMiddleware._send_new_user_notification(
                            event, user_id, group_id, stp_repo
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
        """Обработчик выхода из группы.

        Args:
            group_id: Идентификатор группы Telegram
            user_id: Идентификатор пользователя Telegram
            stp_repo: Репозиторий операций с базой STP
            was_kicked: Был ли пользователь исключен или вышел сам
        """
        try:
            # Проверяем, существует ли пользователь в группе перед удалением
            is_member = await stp_repo.group_member.is_member(group_id, user_id)

            if is_member:
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
            else:
                action = "исключен" if was_kicked else "покинул группу"
                logger.info(
                    f"[Группы] Пользователь {user_id} {action}, но уже отсутствует в участниках группы {group_id}"
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
    ) -> None:
        """Банит пользователя в группе при обработке ChatMemberUpdated событий.

        Args:
            event: Событие изменения участника
            user_id: Идентификатор пользователя Telegram для бана
            group_id: Идентификатор группы Telegram
            stp_repo: Репозиторий операций с базой STP
        """
        await GroupsMiddleware._execute_ban(
            bot=event.bot,
            user_id=user_id,
            group_id=group_id,
            stp_repo=stp_repo,
            reason_text="был заблокирован при попытке присоединения к группе",
        )

    @staticmethod
    async def _validate_user_employment(
        user_id: int,
        group_id: int,
        group,
        stp_repo: MainRequestsRepo,
        user=None,
    ) -> bool:
        """Проверяет, может ли пользователь находиться в группе согласно ее настройкам.

        Args:
            user_id: Идентификатор пользователя Telegram
            group_id: Идентификатор группы Telegram
            group: Экземпляр группы
            stp_repo: Репозиторий операций с базой STP
            user: Экземпляр пользователя с моделью Employee

        Returns:
            True если пользователь может находиться в группе, False если должен быть удален
        """
        try:
            # Игнорируем всех ботов, используя API Telegram
            if user and user.is_bot:
                logger.debug(
                    f"[Группы] Пользователь {user_id} определен как бот, игнорируем проверку"
                )
                return True
            # Если настройка remove_unemployed отключена, разрешаем всех
            if not group.remove_unemployed:
                # Проверяем доступ по ролям, если список ролей не пустой
                if hasattr(group, "allowed_roles") and group.allowed_roles:
                    return await GroupsMiddleware._check_user_role_access(
                        user_id, group, stp_repo
                    )
                return True

            # Проверяем, является ли пользователь активным сотрудником
            employee = await stp_repo.employee.get_users(user_id=user_id)

            if not employee:
                logger.info(
                    f"[Группы] Пользователь {user_id} не найден в базе сотрудников (группа {group_id})"
                )
                return False

            # Дополнительно проверяем доступ по ролям, если список ролей не пустой
            if hasattr(group, "allowed_roles") and group.allowed_roles:
                role_access = await GroupsMiddleware._check_user_role_access(
                    user_id, group, stp_repo
                )
                if not role_access:
                    logger.info(
                        f"[Группы] Пользователь {user_id} не имеет доступа по ролям к группе {group_id}"
                    )
                    return False

            logger.debug(
                f"[Группы] Пользователь {user_id} найден в базе сотрудников: {employee.position or 'Без должности'}"
            )
            return True

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка при проверке статуса сотрудника {user_id} в группе {group_id}: {e}"
            )
            # В случае ошибки разрешаем пользователю остаться
            return True

    @staticmethod
    async def _check_user_role_access(
        user_id: int,
        group: Group,
        stp_repo: MainRequestsRepo,
    ) -> bool:
        """Проверяет, имеет ли пользователь доступ к группе по ролям.

        Args:
            user_id: Идентификатор пользователя Telegram
            group: Экземпляр группы
            stp_repo: Репозиторий операций с базой STP

        Returns:
            True если пользователь имеет доступ, False если нет
        """
        try:
            # Если список разрешенных ролей пуст, разрешаем доступ всем
            if not group.allowed_roles:
                return True

            # Получаем пользователя из базы
            user = await stp_repo.employee.get_users(user_id=user_id)
            if not user:
                logger.info(
                    f"[Группы] Пользователь {user_id} не найден в базе пользователей"
                )
                return False

            # Проверяем, есть ли роль пользователя в списке разрешенных
            user_role = getattr(user, "role", 0)  # По умолчанию роль 0 (не авторизован)

            if user_role in group.allowed_roles or user_role == 10:
                logger.debug(
                    f"[Группы] Пользователь {user_id} имеет доступ (роль {user_role})"
                )
                return True
            else:
                logger.info(
                    f"[Группы] Пользователь {user_id} не имеет доступа (роль {user_role} не в списке {group.allowed_roles})"
                )
                return False

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка при проверке ролей пользователя {user_id}: {e}"
            )
            # В случае ошибки разрешаем доступ
            return True

    @staticmethod
    async def _send_new_user_notification(
        event: ChatMemberUpdated,
        user_id: int,
        group_id: int,
        stp_repo: MainRequestsRepo,
    ):
        """Отправляет уведомление о новом участнике группы.

        Args:
            event: Событие входа в чат
            user_id: Идентификатор пользователя Telegram
            group_id: Идентификатор группы Telegram
            stp_repo: Репозиторий операций с базой STP
        """
        try:
            user = event.new_chat_member.user
            user_mention = f"@{user.username}" if user.username else f"#{user_id}"
            user_fullname = f"{user.first_name or ''} {user.last_name or ''}".strip()

            # Формируем информацию о пользователе
            if user_fullname:
                user_info = f"{user_fullname} ({user_mention})"
            else:
                user_info = user_mention

            # Проверяем, является ли пользователь сотрудником
            employee = await stp_repo.employee.get_users(user_id=user_id)

            if employee:
                # Формируем сообщение для сотрудника
                notification_text = (
                    f"👋 <b>Добро пожаловать в группу!</b>\n\n"
                    f"{
                        format_fullname(
                            employee.fullname,
                            True,
                            True,
                            employee.username,
                            employee.user_id,
                        )
                    } присоединился к группе\n"
                    f"<i>Должность: {employee.position + ' ' + employee.division or 'Не указана'}</i>"
                )
            else:
                # Формируем сообщение для обычного пользователя
                notification_text = (
                    f"👋 <b>Новый участник</b>\n\n{user_info} присоединился к группе"
                )

            await event.bot.send_message(
                chat_id=group_id, text=notification_text, parse_mode="HTML"
            )

            logger.info(
                f"[Группы] Отправлено уведомление о новом участнике {user_id} в группе {group_id}"
            )

        except TelegramForbiddenError as e:
            # Проверяем, что бот был исключен из группы
            if "bot was kicked from the supergroup chat" in str(e):
                logger.warning(
                    f"[Группы] Бот был исключен из группы {group_id}, выполняется очистка данных"
                )
                await GroupsMiddleware._cleanup_removed_group(group_id, stp_repo)
            else:
                logger.error(
                    f"[Группы] Ошибка доступа при отправке уведомления о новом участнике {user_id} в группе {group_id}: {e}"
                )
        except Exception as e:
            logger.error(
                f"[Группы] Ошибка при отправке уведомления о новом участнике {user_id} в группе {group_id}: {e}"
            )

    @staticmethod
    async def _execute_ban(
        bot,
        user_id: int,
        group_id: int,
        stp_repo: MainRequestsRepo,
        reason_text: str,
    ):
        """Общий метод для выполнения бана пользователя.

        Args:
            bot: Экземпляр бота
            user_id: Идентификатор пользователя Telegram
            group_id: Идентификатор группы Telegram
            stp_repo: Репозиторий операций с базой STP
            reason_text: Причина бана
        """
        try:
            # Баним пользователя в Telegram группе
            await bot.ban_chat_member(chat_id=group_id, user_id=user_id)

            # Удаляем пользователя из таблицы group_members
            await stp_repo.group_member.remove_member(group_id, user_id)

            # Отправляем уведомление в группу
            user = await stp_repo.employee.get_users(user_id=user_id)
            if user:
                notification_text = (
                    f"🚫 <b>Пользователь заблокирован</b>\n\n"
                    f"{format_fullname(user.fullname, True, user.username, user.user_id)} {reason_text}\n\n"
                    f"<i>Причина: недостаточно прав доступа к группе</i>"
                )
            else:
                notification_text = (
                    f"🚫 <b>Пользователь заблокирован</b>\n\n"
                    f"{user_id} {reason_text}\n\n"
                    f"<i>Причина: недостаточно прав доступа к группе</i>"
                )

            await bot.send_message(
                chat_id=group_id, text=notification_text, parse_mode="HTML"
            )

            logger.info(
                f"[Группы] Пользователь {user_id} забанен и удален из группы {group_id}"
            )

        except TelegramForbiddenError as e:
            # Проверяем, что бот был исключен из группы
            if "bot was kicked from the supergroup chat" in str(e):
                logger.warning(
                    f"[Группы] Бот был исключен из группы {group_id}, выполняется очистка данных"
                )
                await GroupsMiddleware._cleanup_removed_group(group_id, stp_repo)
            else:
                logger.error(
                    f"[Группы] Ошибка доступа при бане пользователя {user_id} из группы {group_id}: {e}"
                )
        except Exception as e:
            logger.error(
                f"[Группы] Ошибка при бане пользователя {user_id} из группы {group_id}: {e}"
            )

    @staticmethod
    async def _check_and_delete_service_message(
        event: Message,
        stp_repo: MainRequestsRepo,
    ) -> bool:
        """Проверяет, является ли сообщение сервисным и должно ли быть удалено согласно настройкам группы.

        Args:
            event: Сообщение для проверки
            stp_repo: Репозиторий операций с базой STP

        Returns:
            True если сообщение было удалено, False если нет
        """
        try:
            group_id = event.chat.id

            # Получаем настройки группы
            group = await stp_repo.group.get_groups(group_id)
            if not group:
                return False

            # Проверяем, есть ли настройки для удаления сервисных сообщений
            service_categories = getattr(group, "service_messages", []) or []
            if not service_categories:
                return False

            # Определяем тип сервисного сообщения
            message_category = GroupsMiddleware._detect_service_message_category(event)
            if not message_category:
                return False  # Не сервисное сообщение

            # Проверяем, нужно ли удалять этот тип сообщений
            should_delete = message_category in service_categories

            if should_delete:
                # Удаляем сообщение
                await event.delete()
                logger.info(
                    f"[Группы] Удалено сервисное сообщение типа '{message_category}' в группе {group_id}"
                )
                return True

            return False

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка при проверке сервисного сообщения в группе {event.chat.id}: {e}"
            )
            return False

    @staticmethod
    def _detect_service_message_category(message: Message) -> str | None:
        """Определяет категорию сервисного сообщения.

        Args:
            message: Сообщение для анализа

        Returns:
            Категория сообщения или None если не сервисное
        """
        # join: Новый пользователь присоединился
        if message.new_chat_members:
            return "join"

        # leave: Пользователь покинул чат
        if message.left_chat_member:
            return "leave"

        # photo: Изменение фото чата
        if message.new_chat_photo:
            return "photo"

        # photo: Удаление фото чата
        if message.delete_chat_photo:
            return "photo"

        # title: Изменение названия чата
        if message.new_chat_title:
            return "title"

        # pin: Закрепление сообщения
        if message.pinned_message:
            return "pin"

        # videochat: Видеозвонки
        if (
            message.video_chat_started
            or message.video_chat_ended
            or message.video_chat_participants_invited
            or message.video_chat_scheduled
        ):
            return "videochat"

        # other: Прочие сервисные сообщения
        if (
            message.group_chat_created
            or message.supergroup_chat_created
            or message.channel_chat_created
            or message.migrate_to_chat_id
            or message.migrate_from_chat_id
            or message.successful_payment
            or message.connected_website
            or message.proximity_alert_triggered
            or message.message_auto_delete_timer_changed
            or message.web_app_data
            or message.passport_data
        ):
            return "other"

        return None

    @staticmethod
    async def _handle_unregistered_group_command(
        event: Message,
        stp_repo: MainRequestsRepo,
    ) -> bool:
        """Обрабатывает команды бота в незарегистрированных группах.

        Если группа не зарегистрирована и пользователь использует команду бота,
        запрашивает админские права и регистрирует группу при их получении.

        Args:
            event: Сообщение с командой
            stp_repo: Репозиторий операций с базой STP

        Returns:
            True если команда была обработана, False если нет
        """
        try:
            # Проверяем, является ли сообщение командой бота
            if not GroupsMiddleware._is_bot_command(event):
                return False

            group_id = event.chat.id
            user_id = event.from_user.id if event.from_user else None

            if not user_id:
                return False

            # Проверяем, зарегистрирована ли группа
            group = await stp_repo.group.get_groups(group_id)
            if group:
                return False  # Группа уже зарегистрирована, не обрабатываем

            logger.info(
                f"[Группы] Команда {event.text} от пользователя {user_id} в незарегистрированной группе {group_id}"
            )

            # Проверяем, есть ли у бота админские права
            has_admin = await GroupsMiddleware._check_bot_admin_rights(event, group_id)

            if has_admin:
                # У бота есть админские права - регистрируем группу
                await GroupsMiddleware._create_group_in_database(
                    group_id, user_id, stp_repo
                )
                logger.info(
                    f"[Группы] Группа {group_id} автоматически зарегистрирована с админскими правами"
                )
                return False  # Позволяем команде продолжить выполнение
            else:
                # Просим админские права
                await GroupsMiddleware._request_admin_rights(event, group_id)
                return True  # Команда обработана, дальше не продолжаем

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка при обработке команды в незарегистрированной группе {event.chat.id}: {e}"
            )
            return False

    @staticmethod
    def _is_bot_command(message: Message) -> bool:
        """Проверяет, является ли сообщение командой бота.

        Args:
            message: Сообщение для проверки

        Returns:
            True если это команда бота, False если нет
        """
        if not message.text:
            return False

        text = message.text.strip()
        if not text.startswith("/"):
            return False

        # Список команд бота, которые должны работать в группах
        bot_commands = [
            "/admins",
            "/balance",
            "/top",
            "/slots",
            "/dice",
            "/darts",
            "/bowling",
            "/mute",
            "/unmute",
            "/ban",
            "/unban",
            "/pin",
            "/unpin",
            "/settings",
        ]

        # Проверяем, начинается ли текст с одной из команд
        for command in bot_commands:
            if text.startswith(command):
                return True

        return False

    @staticmethod
    async def _check_bot_admin_rights(event: Message, group_id: int) -> bool:
        """Проверяет, есть ли у бота права администратора в группе.

        Args:
            event: Событие сообщения
            group_id: Идентификатор группы Telegram

        Returns:
            True если у бота есть права администратора, False если нет
        """
        try:
            bot_member = await event.bot.get_chat_member(group_id, event.bot.id)
            return bot_member.status in ["administrator", "creator"]
        except Exception as e:
            logger.error(
                f"[Группы] Ошибка при проверке прав бота в группе {group_id}: {e}"
            )
            return False

    @staticmethod
    async def _request_admin_rights(event: Message, group_id: int):
        """Отправляет сообщение с просьбой предоставить боту права администратора.

        Args:
            event: Событие сообщения
            group_id: Репозиторий операций с базой STP
        """
        try:
            request_message = (
                "🤖 <b>Требуются права администратора</b>\n\n"
                "Для использования команд бота в этой группе необходимо предоставить боту права администратора.\n\n"
                "<b>Как предоставить права:</b>\n"
                "1. Перейди в настройки группы\n"
                "2. Выбери <b>Администраторы</b> → <b>Добавить администратора</b>"
                "3. Найди и выбери меня в списке\n"
                "4. Предоставь все права\n\n"
                "После предоставления прав группа будет автоматически зарегистрирована"
            )

            await event.reply(request_message, parse_mode="HTML")

            logger.info(
                f"[Группы] Отправлен запрос на админские права для группы {group_id}"
            )

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка при отправке запроса админских прав для группы {group_id}: {e}"
            )

    @staticmethod
    async def _create_group_in_database(
        group_id: int, invited_by: int, stp_repo: MainRequestsRepo
    ):
        """Создает группу в базе данных.

        Args:
            group_id: Идентификатор группы Telegram
            invited_by: Идентификатор пользователя Telegram, пригласившего бота
            stp_repo: Репозиторий операций с базой STP
        """
        try:
            # Добавляем группу с дефолтными настройками
            group = await stp_repo.group.add_group(
                group_id=group_id, invited_by=invited_by
            )

            if group:
                logger.info(
                    f"[Группы] Группа {group_id} успешно создана в базе данных (приглашен пользователем {invited_by})"
                )
            else:
                logger.warning(
                    f"[Группы] Не удалось создать группу {group_id} в базе данных"
                )

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка при создании группы {group_id} в базе данных: {e}"
            )

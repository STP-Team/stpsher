"""Middleware для операций с группами."""

import logging
from typing import Any, Awaitable, Callable, Dict, Optional, Union

from aiogram import BaseMiddleware, Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import CallbackQuery, ChatMemberUpdated, InlineQuery, Message, User
from stp_database import MainRequestsRepo
from stp_database.models.STP.group import Group

from tgbot.misc.helpers import format_fullname

logger = logging.getLogger(__name__)

# Конфигурация команд бота для групп
BOT_COMMANDS = [
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

# Категории сервисных сообщений
SERVICE_MESSAGE_TYPES = {
    "join": ["new_chat_members"],
    "leave": ["left_chat_member"],
    "photo": ["new_chat_photo", "delete_chat_photo"],
    "title": ["new_chat_title"],
    "pin": ["pinned_message"],
    "videochat": [
        "video_chat_started",
        "video_chat_ended",
        "video_chat_participants_invited",
        "video_chat_scheduled",
    ],
    "other": [
        "group_chat_created",
        "supergroup_chat_created",
        "channel_chat_created",
        "migrate_to_chat_id",
        "migrate_from_chat_id",
        "successful_payment",
        "connected_website",
        "proximity_alert_triggered",
        "message_auto_delete_timer_changed",
        "web_app_data",
        "passport_data",
    ],
}


class GroupsMiddleware(BaseMiddleware):
    """Middleware для управления группами и их участниками.

    Организация:
    1. Основной обработчик
    2. Обработка сообщений
    3. Обработка участников
    4. Валидация и проверки
    5. Уведомления и баны
    6. Сервисные сообщения
    7. Регистрация групп
    8. Вспомогательные методы
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
        """Основной обработчик middleware."""
        stp_repo: MainRequestsRepo = data.get("stp_repo")

        if isinstance(event, Message) and event.chat.type in ["groups", "supergroup"]:
            return await self._handle_message_event(event, stp_repo, handler, data)
        elif isinstance(event, ChatMemberUpdated) and event.chat.type in [
            "groups",
            "supergroup",
        ]:
            await self._handle_membership_event(event, stp_repo)

        return await handler(event, data)

    async def _handle_message_event(
        self,
        event: Message,
        stp_repo: MainRequestsRepo,
        handler: Callable,
        data: Dict[str, Any],
    ) -> Any:
        """Обработка событий сообщений в группах."""
        # Обработка команд в незарегистрированных группах
        if await self._handle_unregistered_group_command(event, stp_repo):
            return None

        # Обработка сервисных сообщений
        if await self._handle_service_message_deletion(event, stp_repo):
            return None

        # Обновление участников группы
        await self._update_group_membership(event, stp_repo)

        return await handler(event, data)

    async def _update_group_membership(
        self, event: Message, stp_repo: MainRequestsRepo
    ) -> None:
        """Обновление участников группы при отправке сообщений."""
        if not event.from_user or event.from_user.is_bot:
            return

        group_id = event.chat.id
        user_id = event.from_user.id

        try:
            group = await self._get_group_or_return(group_id, stp_repo)
            if not group:
                return

            access_granted, denial_reason = await self._validate_user_access(
                user_id, group, stp_repo, event.from_user
            )
            if not access_granted:
                await self._execute_user_kick(
                    event.bot,
                    user_id,
                    group_id,
                    stp_repo,
                    "исключен из группы",
                    denial_reason,
                )
                return

            if not await stp_repo.group_member.is_member(group_id, user_id):
                await self._add_group_member(group_id, user_id, stp_repo)

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка обновления участников группы {group_id} для {user_id}: {e}"
            )

    async def _handle_membership_event(
        self, event: ChatMemberUpdated, stp_repo: MainRequestsRepo
    ) -> None:
        """Обработка событий изменения участников группы."""
        if (
            not event.new_chat_member
            or not event.new_chat_member.user
            or event.new_chat_member.user.is_bot
        ):
            return

        group_id = event.chat.id
        user_id = event.new_chat_member.user.id

        try:
            group = await self._get_group_or_return(group_id, stp_repo)
            if not group:
                return

            old_status = (
                event.old_chat_member.status if event.old_chat_member else "left"
            )
            new_status = event.new_chat_member.status

            logger.info(
                f"[Группы] Изменение статуса {user_id} в группе {group_id}: {old_status} -> {new_status}"
            )

            if self._is_user_joining(old_status, new_status):
                await self._handle_user_join(event, group_id, user_id, group, stp_repo)
            elif self._is_user_leaving(old_status, new_status):
                await self._handle_user_leave(
                    group_id, user_id, stp_repo, new_status == "kicked"
                )

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка обработки участника {user_id} в группе {group_id}: {e}"
            )

    def _is_user_joining(self, old_status: str, new_status: str) -> bool:
        """Проверка присоединения к группе."""
        return old_status in ["left", "kicked"] and new_status in [
            "member",
            "administrator",
            "creator",
        ]

    def _is_user_leaving(self, old_status: str, new_status: str) -> bool:
        """Проверка выхода из группы."""
        return old_status in ["member", "administrator", "creator"] and new_status in [
            "left",
            "kicked",
        ]

    async def _handle_user_join(
        self,
        event: ChatMemberUpdated,
        group_id: int,
        user_id: int,
        group: Group,
        stp_repo: MainRequestsRepo,
    ) -> None:
        """Обработка добавления пользователя в группу."""
        try:
            access_granted, denial_reason = await self._validate_user_access(
                user_id, group, stp_repo, event.new_chat_member.user
            )
            if not access_granted:
                await self._execute_user_kick(
                    event.bot,
                    user_id,
                    group_id,
                    stp_repo,
                    "исключен при присоединении",
                    denial_reason,
                )
                return

            if not await stp_repo.group_member.is_member(group_id, user_id):
                await self._add_group_member(group_id, user_id, stp_repo)

                if group.new_user_notify:
                    await self._send_user_notification(
                        event, user_id, group_id, stp_repo
                    )

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка добавления пользователя {user_id} в группу {group_id}: {e}"
            )

    async def _handle_user_leave(
        self,
        group_id: int,
        user_id: int,
        stp_repo: MainRequestsRepo,
        was_kicked: bool = False,
    ) -> None:
        """Обработка выхода пользователя из группы."""
        try:
            if await stp_repo.group_member.is_member(group_id, user_id):
                result = await stp_repo.group_member.remove_member(group_id, user_id)
                action = "исключен" if was_kicked else "покинул группу"

                if result:
                    logger.info(
                        f"[Группы] Пользователь {user_id} {action} и удален из группы {group_id}"
                    )
                else:
                    logger.warning(
                        f"[Группы] Не удалось удалить {user_id} из группы {group_id}"
                    )

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка удаления пользователя {user_id} из группы {group_id}: {e}"
            )

    async def _get_group_or_return(
        self, group_id: int, stp_repo: MainRequestsRepo
    ) -> Optional[Group]:
        """Получение группы из базы данных."""
        try:
            return await stp_repo.group.get_groups(group_id)
        except Exception as e:
            logger.error(f"[Группы] Ошибка получения группы {group_id}: {e}")
            return None

    async def _validate_user_access(
        self,
        user_id: int,
        group: Group,
        stp_repo: MainRequestsRepo,
        user: Optional[User] = None,
    ) -> tuple[bool, str]:
        """Проверка доступа пользователя к группе."""
        try:
            if user and user.is_bot:
                return True, ""

            # Получаем данные сотрудника для проверок
            employee = await stp_repo.employee.get_users(user_id=user_id)

            # Проверка на удаление уволенных
            if group.remove_unemployed and not employee:
                logger.info(
                    f"[Группы] Пользователь {user_id} не найден в базе сотрудников"
                )
                return False, "уровень доступа"

            # Проверка ролей (только если установлены ограничения)
            if group.allowed_roles:
                if not employee or employee.role not in group.allowed_roles:
                    return False, "уровень доступа"

            # Проверка подразделений (только если установлены ограничения)
            if group.allowed_divisions:
                if not employee or employee.division not in group.allowed_divisions:
                    return False, "направление"
                else:
                    # Проверка должностей (только если подразделение прошло проверку и установлены ограничения по должностям)
                    if group.allowed_positions:
                        if (
                            not employee
                            or employee.position not in group.allowed_positions
                        ):
                            return False, "должность"

            return True, ""

        except Exception as e:
            logger.error(f"[Группы] Ошибка валидации пользователя {user_id}: {e}")
            return True, ""

    async def _execute_user_kick(
        self,
        bot: Bot,
        user_id: int,
        group_id: int,
        stp_repo: MainRequestsRepo,
        reason: str,
        denial_reason: str = "недостаточно прав доступа",
    ) -> None:
        """Выполнение исключения пользователя."""
        try:
            # Используем ban_chat_member с последующим unban для исключения без блокировки
            await bot.ban_chat_member(chat_id=group_id, user_id=user_id)
            await bot.unban_chat_member(chat_id=group_id, user_id=user_id)
            await stp_repo.group_member.remove_member(group_id, user_id)

            await self._send_kick_notification(
                bot, user_id, group_id, stp_repo, reason, denial_reason
            )
            logger.info(
                f"[Группы] Пользователь {user_id} исключен из группы {group_id}"
            )

        except TelegramForbiddenError as e:
            if "bot was kicked from the supergroup chat" in str(e):
                await self._cleanup_removed_group(group_id, stp_repo)
            else:
                logger.error(
                    f"[Группы] Ошибка доступа при исключении {user_id} из группы {group_id}: {e}"
                )
        except Exception as e:
            logger.error(
                f"[Группы] Ошибка исключения пользователя {user_id} из группы {group_id}: {e}"
            )

    async def _send_kick_notification(
        self,
        bot: Bot,
        user_id: int,
        group_id: int,
        stp_repo: MainRequestsRepo,
        reason: str,
        denial_reason: str = "недостаточно прав доступа",
    ) -> None:
        """Отправка уведомления об исключении."""
        try:
            user = await stp_repo.employee.get_users(user_id=user_id)
            reason_map = {
                "уровень доступа": "неразрешенный уровень доступа",
                "направление": "неразрешенное направление",
                "должность": "неразрешенная должность",
            }
            reason_text = reason_map.get(denial_reason, "недостаточно прав доступа")
            if user:
                text = f"👋 <b>Пользователь исключен</b>\n\n{format_fullname(user, True)} {reason}\n\n<i>Причина: {reason_text}</i>"
            else:
                text = f"👋 <b>Пользователь исключен</b>\n\n{user_id} {reason}\n\n<i>Причина: {reason_text}</i>"

            await bot.send_message(chat_id=group_id, text=text, parse_mode="HTML")

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка отправки уведомления об исключении {user_id}: {e}"
            )

    async def _send_user_notification(
        self,
        event: ChatMemberUpdated,
        user_id: int,
        group_id: int,
        stp_repo: MainRequestsRepo,
    ) -> None:
        """Отправка уведомления о новом участнике."""
        try:
            user = event.new_chat_member.user
            employee = await stp_repo.employee.get_users(user_id=user_id)

            if employee:
                text = (
                    f"👋 <b>Добро пожаловать в группу!</b>\n\n"
                    f"{format_fullname(employee, True, True)} присоединился к группе\n"
                    f"<i>Должность: {employee.position + ' ' + employee.division or 'Не указана'}</i>"
                )
            else:
                user_mention = f"@{user.username}" if user.username else f"#{user_id}"
                user_fullname = (
                    f"{user.first_name or ''} {user.last_name or ''}".strip()
                )
                user_info = (
                    f"{user_fullname} ({user_mention})"
                    if user_fullname
                    else user_mention
                )
                text = f"👋 <b>Новый участник</b>\n\n{user_info} присоединился к группе"

            await event.bot.send_message(chat_id=group_id, text=text, parse_mode="HTML")

        except TelegramForbiddenError as e:
            if "bot was kicked from the supergroup chat" in str(e):
                await self._cleanup_removed_group(group_id, stp_repo)
        except Exception as e:
            logger.error(
                f"[Группы] Ошибка отправки уведомления о новом участнике {user_id}: {e}"
            )

    async def _add_group_member(
        self, group_id: int, user_id: int, stp_repo: MainRequestsRepo
    ) -> None:
        """Добавление участника в группу."""
        try:
            result = await stp_repo.group_member.add_member(group_id, user_id)
            if result:
                logger.info(f"[Группы] Добавлен участник {user_id} в группу {group_id}")
            else:
                logger.warning(
                    f"[Группы] Не удалось добавить участника {user_id} в группу {group_id}"
                )
        except Exception as e:
            logger.error(
                f"[Группы] Ошибка добавления участника {user_id} в группу {group_id}: {e}"
            )

    async def _handle_service_message_deletion(
        self, event: Message, stp_repo: MainRequestsRepo
    ) -> bool:
        """Обработка удаления сервисных сообщений."""
        try:
            group = await self._get_group_or_return(event.chat.id, stp_repo)
            if not group:
                return False

            service_categories = getattr(group, "service_messages", []) or []
            if not service_categories:
                return False

            message_category = self._detect_service_message_category(event)
            if not message_category or message_category not in service_categories:
                return False

            await event.delete()
            logger.info(
                f"[Группы] Удалено сервисное сообщение '{message_category}' в группе {event.chat.id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка обработки сервисного сообщения в группе {event.chat.id}: {e}"
            )
            return False

    def _detect_service_message_category(self, message: Message) -> Optional[str]:
        """Определение категории сервисного сообщения."""
        for category, attributes in SERVICE_MESSAGE_TYPES.items():
            if any(getattr(message, attr, None) for attr in attributes):
                return category
        return None

    async def _handle_unregistered_group_command(
        self, event: Message, stp_repo: MainRequestsRepo
    ) -> bool:
        """Обработка команд в незарегистрированных группах."""
        if not self._is_bot_command(event) or not event.from_user:
            return False

        group_id = event.chat.id
        user_id = event.from_user.id

        try:
            group = await stp_repo.group.get_groups(group_id)
            if group:
                return False  # Группа уже зарегистрирована

            logger.info(
                f"[Группы] Команда {event.text} в незарегистрированной группе {group_id}"
            )

            if await self._check_bot_admin_rights(event, group_id):
                await self._create_group_in_database(group_id, user_id, stp_repo)
                return False  # Позволяем команде выполниться
            else:
                await self._request_admin_rights(event)
                return True  # Команда обработана

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка обработки команды в незарегистрированной группе {group_id}: {e}"
            )
            return False

    def _is_bot_command(self, message: Message) -> bool:
        """Проверка, является ли сообщение командой бота."""
        if not message.text:
            return False
        text = message.text.strip()
        return text.startswith("/") and any(
            text.startswith(cmd) for cmd in BOT_COMMANDS
        )

    async def _check_bot_admin_rights(self, event: Message, group_id: int) -> bool:
        """Проверка прав администратора у бота."""
        try:
            bot_member = await event.bot.get_chat_member(group_id, event.bot.id)
            return bot_member.status in ["administrator", "creator"]
        except Exception as e:
            logger.error(f"[Группы] Ошибка проверки прав бота в группе {group_id}: {e}")
            return False

    async def _request_admin_rights(self, event: Message) -> None:
        """Запрос прав администратора."""
        text = (
            "🤖 <b>Требуются права администратора</b>\n\n"
            "Для использования команд бота в этой группе необходимо предоставить боту права администратора.\n\n"
            "<b>Как предоставить права:</b>\n"
            "1. Перейди в настройки группы\n"
            "2. Выбери <b>Администраторы</b> → <b>Добавить администратора</b>\n"
            "3. Найди и выбери меня в списке\n"
            "4. Предоставь все права\n\n"
            "После предоставления прав группа будет автоматически зарегистрирована"
        )
        await event.reply(text, parse_mode="HTML")

    async def _create_group_in_database(
        self, group_id: int, invited_by: int, stp_repo: MainRequestsRepo
    ) -> None:
        """Создание группы в базе данных."""
        try:
            group = await stp_repo.group.add_group(
                group_id=group_id, group_type="group", invited_by=invited_by
            )
            if group:
                logger.info(
                    f"[Группы] Группа {group_id} создана в базе (приглашен {invited_by})"
                )
            else:
                logger.warning(f"[Группы] Не удалось создать группу {group_id} в базе")
        except Exception as e:
            logger.error(f"[Группы] Ошибка создания группы {group_id} в базе: {e}")

    async def _cleanup_removed_group(
        self, group_id: int, stp_repo: MainRequestsRepo
    ) -> None:
        """Очистка данных удаленной группы."""
        try:
            await stp_repo.group_member.remove_all_members(group_id)
            await stp_repo.group.delete_group(group_id)
            logger.info(f"[Группы] Очищены данные группы {group_id}")
        except Exception as e:
            logger.error(f"[Группы] Ошибка очистки данных группы {group_id}: {e}")

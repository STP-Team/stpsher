"""Middleware для операций с группами."""

import logging
from typing import Any, Awaitable, Callable, Dict, Optional, TypeAlias, Union

from aiogram import BaseMiddleware, Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import CallbackQuery, ChatMemberUpdated, InlineQuery, Message, User
from stp_database.models.STP.group import Group
from stp_database.repo.STP import MainRequestsRepo

from tgbot.misc.helpers import format_fullname

logger = logging.getLogger(__name__)

# Type aliases for better readability
EventType: TypeAlias = Union[Message, CallbackQuery, InlineQuery, ChatMemberUpdated]
HandlerType: TypeAlias = Callable[[EventType, Dict[str, Any]], Awaitable[Any]]

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

# Статусы участников чата
MEMBER_STATUSES = {
    "JOINING": ["left", "kicked"],
    "ACTIVE": ["member", "administrator", "creator"],
    "LEAVING": ["left", "kicked"],
}

# Причины отказа в доступе и их описания
ACCESS_DENIAL_REASONS = {
    "уровень доступа": "неразрешенный уровень доступа",
    "направление": "неразрешенное направление",
    "должность": "неразрешенная должность",
}

# Тексты уведомлений
NOTIFICATIONS = {
    "user_kicked": "👋 <b>Пользователь исключен</b>\n\n{user_info} {reason}\n\n<i>Причина: {reason_text}</i>",
    "user_welcome": "👋 <b>Добро пожаловать в группу!</b>\n\n{user_info} присоединился к группе\n<i>Должность: {position}</i>",
    "user_new": "👋 <b>Новый участник</b>\n\n{user_info} присоединился к группе",
    "admin_rights_required": (
        "🤖 <b>Требуются права администратора</b>\n\n"
        "Для использования команд бота в этой группе необходимо предоставить боту права администратора.\n\n"
        "<b>Как предоставить права:</b>\n"
        "1. Перейди в настройки группы\n"
        "2. Выбери <b>Администраторы</b> → <b>Добавить администратора</b>\n"
        "3. Найди и выбери меня в списке\n"
        "4. Предоставь все права\n\n"
        "После предоставления прав группа будет автоматически зарегистрирована"
    ),
}

# Поддерживаемые типы групп
SUPPORTED_GROUP_TYPES = ["groups", "supergroup"]

# Административные статусы
ADMIN_STATUSES = ["administrator", "creator"]


class GroupsMiddleware(BaseMiddleware):
    """Middleware для автоматического управления группами Telegram и их участниками.

    Этот middleware обеспечивает:
    1. Контроль доступа на основе ролей, должностей и подразделений
    2. Автоматическое управление членством в группах
    3. Удаление сервисных сообщений по настройкам группы
    4. Автоматическую регистрацию новых групп с проверкой прав бота
    5. Уведомления о новых участниках и исключениях
    6. Автоматическое исключение пользователей без доступа

    Архитектура:
    - Обработка событий сообщений и изменений участников
    - Кэширование данных сотрудников для оптимизации производительности
    - Централизованная обработка ошибок с автоматической очисткой удаленных групп
    - Использование констант для упрощения конфигурации и поддержки

    Безопасность:
    - Проверка доступа происходит при каждом сообщении и изменении участников
    - Автоматическое исключение неавторизованных пользователей
    - Логирование всех действий по безопасности
    """

    def __init__(self):
        # Отслеживание текущих операций для предотвращения дубликатов
        self._processing_operations: set = set()
        super().__init__()

    async def _safe_execute(
        self,
        operation: str,
        func: Callable,
        *args,
        group_id: Optional[int] = None,
        user_id: Optional[int] = None,
        stp_repo: Optional[MainRequestsRepo] = None,
        **kwargs,
    ) -> Optional[Any]:
        """Безопасное выполнение операций с обработкой ошибок."""
        try:
            return await func(*args, **kwargs)
        except TelegramForbiddenError as e:
            if (
                "bot was kicked from the supergroup chat" in str(e)
                and group_id
                and stp_repo
            ):
                await self._cleanup_removed_group(group_id, stp_repo)
            else:
                user_info = f" для пользователя {user_id}" if user_id else ""
                logger.error(
                    f"[Группы] Ошибка доступа при {operation} в группе {group_id}{user_info}: {e}"
                )
        except Exception as e:
            user_info = f" для пользователя {user_id}" if user_id else ""
            group_info = f" в группе {group_id}" if group_id else ""
            logger.error(f"[Группы] Ошибка {operation}{group_info}{user_info}: {e}")
        return None

    async def _get_user_context(
        self,
        user_id: int,
        group_id: int,
        stp_repo: MainRequestsRepo,
        user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """Получение полного контекста пользователя для обработки доступа и уведомлений.

        Загружает все необходимые данные за один вызов:
        - Информацию о группе из базы данных
        - Данные сотрудника (если найден в корпоративной базе)
        - Telegram-объект пользователя

        Args:
            user_id: Идентификатор пользователя Telegram
            group_id: Идентификатор группы
            stp_repo: Репозиторий для работы с базой данных
            user: Объект пользователя Telegram (опционально)

        Returns:
            Словарь с ключами: group, employee, user, user_id, group_id
        """
        context = {
            "group": await self._get_group_or_return(group_id, stp_repo),
            "employee": await stp_repo.employee.get_users(user_id=user_id),
            "user": user,
            "user_id": user_id,
            "group_id": group_id,
        }
        return context

    async def _process_user_in_group(
        self,
        user_id: int,
        group_id: int,
        stp_repo: MainRequestsRepo,
        bot: Optional[Bot] = None,
        user: Optional[User] = None,
        action: str = "обработки пользователя",
        send_notification: bool = False,
    ) -> bool:
        """Централизованная обработка пользователя в группе с дедупликацией.

        Единственная точка входа для всех операций с пользователями в группах.
        Предотвращает дублирование операций для одного пользователя.

        Args:
            user_id: ID пользователя
            group_id: ID группы
            stp_repo: Репозиторий базы данных
            bot: Экземпляр бота (для Telegram операций)
            user: Объект пользователя Telegram
            action: Описание действия для логирования
            send_notification: Отправлять ли уведомление о новом участнике

        Returns:
            True если пользователь успешно обработан, False если операция уже выполняется
        """
        operation_key = f"{group_id}:{user_id}"

        # Проверяем, не обрабатывается ли уже этот пользователь в этой группе
        if operation_key in self._processing_operations:
            logger.debug(
                f"[Группы] Операция для пользователя {user_id} в группе {group_id} "
                "уже выполняется, пропускаем дублированный запрос"
            )
            return False

        # Добавляем операцию в список обрабатываемых
        self._processing_operations.add(operation_key)

        try:
            # Получаем контекст пользователя
            user_context = await self._get_user_context(
                user_id, group_id, stp_repo, user
            )

            # Выполняем обработку доступа и членства
            result = await self._handle_user_access_and_membership(
                user_context, stp_repo, bot, action
            )

            # Отправляем уведомление если требуется
            if result and send_notification and user_context["group"]:
                group = user_context["group"]
                if group.new_user_notify and bot:
                    await self._send_user_notification_from_context_safe(
                        bot, user_context, stp_repo
                    )

            return result

        except Exception as e:
            logger.error(
                f"[Группы] Ошибка обработки пользователя {user_id} в группе {group_id}: {e}"
            )
            return False
        finally:
            # Убираем операцию из списка обрабатываемых
            self._processing_operations.discard(operation_key)

    async def _handle_user_access_and_membership(
        self,
        user_context: Dict[str, Any],
        stp_repo: MainRequestsRepo,
        bot: Optional[Bot] = None,
        action: str = "проверки доступа",
    ) -> bool:
        """Комплексная обработка доступа пользователя и автоматическое управление членством.

        Основной метод для проверки прав доступа и управления участниками группы:
        1. Проверяет права доступа на основе настроек группы
        2. При отсутствии доступа автоматически исключает пользователя
        3. При наличии доступа добавляет в группу если не является участником
        4. Логирует все действия для аудита безопасности

        Args:
            user_context: Контекст пользователя с данными группы и сотрудника
            stp_repo: Репозиторий для работы с базой данных
            bot: Экземпляр бота для исключения пользователей (если требуется)
            action: Описание действия для логирования

        Returns:
            True если доступ разрешен, False если пользователь исключен
        """
        group = user_context["group"]
        user_id = user_context["user_id"]
        group_id = user_context["group_id"]

        if not group:
            return False

        access_granted, denial_reason = await self._validate_user_access_from_context(
            user_context
        )

        if not access_granted and bot:
            await self._execute_user_kick(
                bot,
                user_id,
                group_id,
                stp_repo,
                f"исключен при {action}",
                denial_reason,
            )
            return False

        if access_granted:
            # Проверяем, что пользователь действительно является участником Telegram группы
            # перед добавлением в базу данных
            if bot and await self._verify_telegram_membership(bot, group_id, user_id):
                # Всегда пытаемся добавить пользователя в группу при наличии доступа
                # _add_group_member теперь обрабатывает дублирование записей gracefully
                await self._add_group_member(group_id, user_id, stp_repo)
            elif not bot:
                # Если нет доступа к боту, добавляем без проверки (для обратной совместимости)
                await self._add_group_member(group_id, user_id, stp_repo)

        return access_granted

    @staticmethod
    async def _validate_user_access_from_context(
        user_context: Dict[str, Any],
    ) -> tuple[bool, str]:
        """Проверка доступа пользователя на основе контекста."""
        group = user_context["group"]
        employee = user_context["employee"]
        user = user_context["user"]

        if user and user.is_bot:
            return True, ""

        # Проверка на удаление уволенных
        if group.remove_unemployed and not employee:
            return False, "уровень доступа"

        # Проверка ролей
        if group.allowed_roles and (
            not employee or employee.role not in group.allowed_roles
        ):
            return False, "уровень доступа"

        # Проверка подразделений
        if group.allowed_divisions:
            if not employee or employee.division not in group.allowed_divisions:
                return False, "направление"

            # Проверка должностей (только если подразделение прошло проверку)
            if group.allowed_positions:
                if not employee or employee.position not in group.allowed_positions:
                    return False, "должность"

        return True, ""

    async def _verify_telegram_membership(
        self, bot: Bot, group_id: int, user_id: int
    ) -> bool:
        """Проверка, что пользователь действительно является участником Telegram группы."""
        try:
            member = await bot.get_chat_member(chat_id=group_id, user_id=user_id)
            # Считаем пользователя участником если он имеет активный статус
            is_member = member.status in MEMBER_STATUSES["ACTIVE"]

            if not is_member:
                logger.debug(
                    f"[Группы] Пользователь {user_id} не является участником группы {group_id} "
                    f"(статус: {member.status})"
                )

            return is_member
        except Exception as e:
            # Если не можем проверить статус, считаем что пользователь не участник
            logger.warning(
                f"[Группы] Не удалось проверить членство {user_id} в группе {group_id}: {e}"
            )
            return False

    async def __call__(
        self,
        handler: HandlerType,
        event: EventType,
        data: Dict[str, Any],
    ) -> Any:
        """Основной обработчик middleware."""
        stp_repo: MainRequestsRepo = data.get("stp_repo")

        if isinstance(event, Message) and event.chat.type in SUPPORTED_GROUP_TYPES:
            return await self._handle_message_event(event, stp_repo, handler, data)
        elif (
            isinstance(event, ChatMemberUpdated)
            and event.chat.type in SUPPORTED_GROUP_TYPES
        ):
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

        await self._safe_execute(
            "обновления участников группы",
            self._process_user_membership,
            event.from_user.id,
            event.chat.id,
            stp_repo,
            event.from_user,
            event.bot,
            "отправки сообщения",
            group_id=event.chat.id,
            user_id=event.from_user.id,
            stp_repo=stp_repo,
        )

    async def _process_user_membership(
        self,
        user_id: int,
        group_id: int,
        stp_repo: MainRequestsRepo,
        user: User,
        bot: Bot,
        action: str,
    ) -> None:
        """Обработка членства пользователя в группе (через централизованный процессор)."""
        await self._process_user_in_group(
            user_id=user_id,
            group_id=group_id,
            stp_repo=stp_repo,
            bot=bot,
            user=user,
            action=action,
            send_notification=False,  # Уведомления только при присоединении, не при сообщениях
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
        return (
            old_status in MEMBER_STATUSES["JOINING"]
            and new_status in MEMBER_STATUSES["ACTIVE"]
        )

    def _is_user_leaving(self, old_status: str, new_status: str) -> bool:
        """Проверка выхода из группы."""
        return (
            old_status in MEMBER_STATUSES["ACTIVE"]
            and new_status in MEMBER_STATUSES["LEAVING"]
        )

    async def _handle_user_join(
        self,
        event: ChatMemberUpdated,
        group_id: int,
        user_id: int,
        group: Group,
        stp_repo: MainRequestsRepo,
    ) -> None:
        """Обработка добавления пользователя в группу."""
        await self._safe_execute(
            "добавления пользователя в группу",
            self._process_user_join,
            event,
            user_id,
            group_id,
            group,
            stp_repo,
            group_id=group_id,
            user_id=user_id,
            stp_repo=stp_repo,
        )

    async def _process_user_join(
        self,
        event: ChatMemberUpdated,
        user_id: int,
        group_id: int,
        group: Group,
        stp_repo: MainRequestsRepo,
    ) -> None:
        """Процесс добавления пользователя в группу (через централизованный процессор)."""
        await self._process_user_in_group(
            user_id=user_id,
            group_id=group_id,
            stp_repo=stp_repo,
            bot=event.bot,
            user=event.new_chat_member.user,
            action="присоединении",
            send_notification=True,  # Отправляем уведомления при присоединении
        )

    async def _send_user_notification_from_context(
        self,
        event: ChatMemberUpdated,
        user_context: Dict[str, Any],
        stp_repo: MainRequestsRepo,
    ) -> None:
        """Отправка уведомления о новом участнике на основе контекста."""
        employee = user_context["employee"]
        user = user_context["user"]
        user_id = user_context["user_id"]
        group_id = user_context["group_id"]

        if employee:
            position = (
                f"{employee.position} {employee.division}".strip() or "Не указана"
            )
            text = NOTIFICATIONS["user_welcome"].format(
                user_info=format_fullname(employee, True, True), position=position
            )
        else:
            user_info = self._format_telegram_user_info(user, user_id)
            text = NOTIFICATIONS["user_new"].format(user_info=user_info)

        await self._safe_execute(
            "отправки уведомления о новом участнике",
            event.bot.send_message,
            chat_id=group_id,
            text=text,
            group_id=group_id,
            user_id=user_id,
            stp_repo=stp_repo,
        )

    async def _send_user_notification_from_context_safe(
        self,
        bot: Bot,
        user_context: Dict[str, Any],
        stp_repo: MainRequestsRepo,
    ) -> None:
        """Безопасная отправка уведомления о новом участнике на основе контекста."""
        employee = user_context["employee"]
        user = user_context["user"]
        user_id = user_context["user_id"]
        group_id = user_context["group_id"]

        if employee:
            position = (
                f"{employee.position} {employee.division}".strip() or "Не указана"
            )
            text = NOTIFICATIONS["user_welcome"].format(
                user_info=format_fullname(employee, True, True), position=position
            )
        else:
            user_info = self._format_telegram_user_info(user, user_id)
            text = NOTIFICATIONS["user_new"].format(user_info=user_info)

        await self._safe_execute(
            "отправки уведомления о новом участнике",
            bot.send_message,
            chat_id=group_id,
            text=text,
            group_id=group_id,
            user_id=user_id,
            stp_repo=stp_repo,
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
            # Всегда пытаемся удалить пользователя, даже если он уже не в базе
            result = await stp_repo.group_member.remove_member(group_id, user_id)
            action = "исключен" if was_kicked else "покинул группу"

            if result:
                logger.info(
                    f"[Группы] Пользователь {user_id} {action} и удален из группы {group_id}"
                )
            else:
                logger.debug(
                    f"[Группы] Пользователь {user_id} уже не был в группе {group_id} при попытке удаления"
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
        user = await stp_repo.employee.get_users(user_id=user_id)
        reason_text = ACCESS_DENIAL_REASONS.get(
            denial_reason, "недостаточно прав доступа"
        )

        user_info = format_fullname(user, True) if user else str(user_id)
        text = NOTIFICATIONS["user_kicked"].format(
            user_info=user_info, reason=reason, reason_text=reason_text
        )

        await self._safe_execute(
            "отправки уведомления об исключении",
            bot.send_message,
            chat_id=group_id,
            text=text,
            group_id=group_id,
            user_id=user_id,
        )

    async def _send_user_notification(
        self,
        event: ChatMemberUpdated,
        user_id: int,
        group_id: int,
        stp_repo: MainRequestsRepo,
    ) -> None:
        """Отправка уведомления о новом участнике."""
        user = event.new_chat_member.user
        employee = await stp_repo.employee.get_users(user_id=user_id)

        if employee:
            position = (
                f"{employee.position} {employee.division}".strip() or "Не указана"
            )
            text = NOTIFICATIONS["user_welcome"].format(
                user_info=format_fullname(employee, True, True), position=position
            )
        else:
            user_info = self._format_telegram_user_info(user, user_id)
            text = NOTIFICATIONS["user_new"].format(user_info=user_info)

        await self._safe_execute(
            "отправки уведомления о новом участнике",
            event.bot.send_message,
            chat_id=group_id,
            text=text,
            group_id=group_id,
            user_id=user_id,
            stp_repo=stp_repo,
        )

    def _format_telegram_user_info(self, user: User, user_id: int) -> str:
        """Форматирование информации о пользователе Telegram."""
        user_mention = f"@{user.username}" if user.username else f"#{user_id}"
        user_fullname = f"{user.first_name or ''} {user.last_name or ''}".strip()
        return f"{user_fullname} ({user_mention})" if user_fullname else user_mention

    async def _add_group_member(
        self, group_id: int, user_id: int, stp_repo: MainRequestsRepo
    ) -> None:
        """Добавление участника в группу с проверкой существования."""
        try:
            # Сначала проверяем, не является ли уже участником
            try:
                if await stp_repo.group_member.is_member(group_id, user_id):
                    logger.debug(
                        f"[Группы] Участник {user_id} уже существует в группе {group_id}"
                    )
                    return
            except Exception as check_ex:
                logger.debug(
                    f"[Группы] Не удалось проверить существование участника {user_id} "
                    f"в группе {group_id}, продолжаем попытку добавления: {check_ex}"
                )

            # Пытаемся добавить участника
            result = await stp_repo.group_member.add_member(group_id, user_id)
            if result:
                logger.info(f"[Группы] Добавлен участник {user_id} в группу {group_id}")
            else:
                logger.warning(
                    f"[Группы] Не удалось добавить участника {user_id} в группу {group_id} "
                    "(метод вернул False)"
                )
        except Exception as e:
            # Обработка ошибки дублирования записи (race condition)
            error_str = str(e).lower()
            is_duplicate_error = any(
                keyword in error_str
                for keyword in [
                    "duplicate",
                    "already exists",
                    "constraint",
                    "1062",
                    "1020",
                    "record has changed",
                    "unique constraint",
                ]
            )

            if is_duplicate_error:
                # Для ошибок дублирования проверяем, что пользователь действительно в базе
                try:
                    if await stp_repo.group_member.is_member(group_id, user_id):
                        logger.debug(
                            f"[Группы] Участник {user_id} уже существует в группе {group_id} "
                            "(обработана ошибка дублирования)"
                        )
                        return
                except Exception as check_ex:
                    logger.debug(
                        f"[Группы] Не удалось проверить существование участника {user_id} "
                        f"в группе {group_id}: {check_ex}"
                    )
                    # Если не можем проверить, но это ошибка дублирования, считаем успешным
                    logger.debug(
                        f"[Группы] Предполагаем, что участник {user_id} уже в группе {group_id} "
                        "(ошибка дублирования)"
                    )
                    return

            # Логируем ошибку только если это не ошибка дублирования или проверка провалилась
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
            return bot_member.status in ADMIN_STATUSES
        except Exception as e:
            logger.error(f"[Группы] Ошибка проверки прав бота в группе {group_id}: {e}")
            return False

    async def _request_admin_rights(self, event: Message) -> None:
        """Запрос прав администратора."""
        await event.reply(NOTIFICATIONS["admin_rights_required"])

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

import logging
from typing import Optional, Sequence, TypedDict, Unpack

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models.STP.group import Group
from infrastructure.database.repo.base import BaseRepo

logger = logging.getLogger(__name__)


class GroupParams(TypedDict, total=False):
    """Доступные параметры для обновления пользователя в таблице RegisteredUsers."""

    group_id: int
    invited_by: str | None
    remove_unemployed: bool | None
    is_casino_allowed: bool | None
    new_user_notify: bool | None
    allowed_roles: list | None
    service_messages: list | None


class GroupRepo(BaseRepo):
    async def get_group(self, group_id: int) -> Optional[Group]:
        """
        Получить группу по идентификатору

        Args:
            group_id: Идентификатор группы Telegram

        Returns:
            Объект Group или None
        """
        try:
            result = await self.session.execute(
                select(Group).where(Group.group_id == group_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения группы {group_id}: {e}")
            return None

    async def get_groups_by_inviter(self, invited_by: int) -> Sequence[Group]:
        """
        Получить все группы, добавленные определенным пользователем

        Args:
            invited_by: Идентификатор пользователя, который пригласил бота

        Returns:
            Список групп
        """
        try:
            result = await self.session.execute(
                select(Group).where(Group.invited_by == invited_by)
            )
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка получения групп для пользователя {invited_by}: {e}"
            )
            return []

    async def get_all_groups(self) -> Sequence[Group]:
        """
        Получить все группы

        Returns:
            Список всех групп
        """
        try:
            result = await self.session.execute(select(Group))
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения списка всех групп: {e}")
            return []

    async def add_group(
        self, group_id: int, invited_by: int, remove_unemployed: bool = True
    ) -> Optional[Group]:
        """
        Добавить новую группу

        Args:
            group_id: Идентификатор группы Telegram
            invited_by: Идентификатор пользователя, который пригласил бота
            remove_unemployed: Удалять уволенных сотрудников из группы

        Returns:
            Объект Group или None при ошибке
        """
        try:
            group = Group(
                group_id=group_id,
                invited_by=invited_by,
                remove_unemployed=remove_unemployed,
            )
            self.session.add(group)
            await self.session.commit()
            return group
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка добавления группы {group_id}: {e}")
            await self.session.rollback()
            return None

    async def update_group(
        self,
        group_id: int = None,
        **kwargs: Unpack[GroupParams],
    ) -> Optional[Group]:
        try:
            select_stmt = select(Group).where(Group.group_id == group_id)

            result = await self.session.execute(select_stmt)
            group: Group | None = result.scalar_one_or_none()

            # Если группа существует - обновляем ее
            if group is not None:
                for key, value in kwargs.items():
                    setattr(group, key, value)
                await self.session.commit()
                logger.info(f"[БД] Группа {group_id} обновлена: {kwargs}")
            else:
                logger.warning(f"[БД] Группа {group_id} не найдена для обновления")

            return group
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка обновления группы {group_id}: {e}")
            await self.session.rollback()
            return None

    async def delete_group(self, group_id: int) -> bool:
        """
        Удалить группу

        Args:
            group_id: Идентификатор группы Telegram

        Returns:
            True если группа удалена, False при ошибке
        """
        try:
            result = await self.session.execute(
                select(Group).where(Group.group_id == group_id)
            )
            group = result.scalar_one_or_none()

            if group:
                await self.session.delete(group)
                await self.session.commit()
                logger.info(f"[БД] Группа {group_id} удалена")
                return True
            else:
                logger.warning(f"[БД] Группа {group_id} не найдена для удаления")
                return False
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка удаления группы {group_id}: {e}")
            await self.session.rollback()
            return False

    async def sync_groups_with_bot_chats(self, bot) -> int:
        """
        Синхронизация групп из БД с чатами, где бот имеет права администратора
        Добавляет отсутствующие группы в БД

        Args:
            bot: Объект бота для получения списка чатов

        Returns:
            Количество добавленных групп
        """
        try:
            from aiogram.types import ChatMemberAdministrator, ChatMemberOwner

            # Получаем все существующие группы из БД
            existing_groups = await self.get_all_groups()
            existing_group_ids = {group.group_id for group in existing_groups}

            # Получаем список всех чатов бота через get_updates
            added_count = 0

            # Используем getUpdates для получения информации о чатах
            updates = await bot.get_updates(limit=100, offset=-1)

            # Собираем уникальные group_id из обновлений
            chat_ids = set()
            for update in updates:
                if hasattr(update, "message") and update.message:
                    chat = update.message.chat
                    if chat.type in ["group", "supergroup"]:
                        chat_ids.add(chat.id)
                elif hasattr(update, "my_chat_member") and update.my_chat_member:
                    chat = update.my_chat_member.chat
                    if chat.type in ["group", "supergroup"]:
                        chat_ids.add(chat.id)

            # Проверяем каждый найденный чат
            for chat_id in chat_ids:
                if chat_id not in existing_group_ids:
                    try:
                        # Проверяем, является ли бот администратором в этой группе
                        chat_member = await bot.get_chat_member(chat_id, bot.id)

                        if isinstance(
                            chat_member, (ChatMemberAdministrator, ChatMemberOwner)
                        ):
                            # Бот - администратор, но группы нет в БД
                            # Добавляем группу с неизвестным пригласившим (0)
                            group = await self.add_group(
                                group_id=chat_id,
                                invited_by=0,  # Неизвестный пригласивший
                            )

                            if group:
                                added_count += 1
                                logger.info(
                                    f"[SYNC] Добавлена отсутствующая группа {chat_id}"
                                )

                    except Exception as chat_error:
                        # Возможно, бот больше не в группе или нет доступа
                        logger.debug(
                            f"[SYNC] Не удалось проверить группу {chat_id}: {chat_error}"
                        )
                        continue

            if added_count > 0:
                logger.info(
                    f"[SYNC] Синхронизация завершена: добавлено {added_count} групп"
                )
            else:
                logger.info("[SYNC] Синхронизация завершена: новых групп не найдено")

            return added_count

        except Exception as e:
            logger.error(f"[SYNC] Ошибка синхронизации групп: {e}")
            return 0

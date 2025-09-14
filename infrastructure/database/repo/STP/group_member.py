import logging
from typing import Optional, Sequence

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models.STP.group_member import GroupMember
from infrastructure.database.repo.base import BaseRepo

logger = logging.getLogger(__name__)


class GroupMemberRepo(BaseRepo):
    async def add_member(self, group_id: int, member_id: int) -> Optional[GroupMember]:
        """
        Добавить участника в группу

        Args:
            group_id: Идентификатор группы Telegram
            member_id: Идентификатор участника Telegram

        Returns:
            Объект GroupMember или None в случае ошибки
        """
        try:
            group_member = GroupMember(group_id=group_id, member_id=member_id)
            self.session.add(group_member)
            await self.session.commit()
            return group_member
        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка добавления участника {member_id} в группу {group_id}: {e}"
            )
            await self.session.rollback()
            return None

    async def remove_member(self, group_id: int, member_id: int) -> bool:
        """
        Удалить участника из группы

        Args:
            group_id: Идентификатор группы Telegram
            member_id: Идентификатор участника Telegram

        Returns:
            True если участник был удален, False в случае ошибки
        """
        try:
            result = await self.session.execute(
                delete(GroupMember).where(
                    GroupMember.group_id == group_id, GroupMember.member_id == member_id
                )
            )
            await self.session.commit()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка удаления участника {member_id} из группы {group_id}: {e}"
            )
            await self.session.rollback()
            return False

    async def get_group_members(self, group_id: int) -> Sequence[GroupMember]:
        """
        Получить всех участников группы

        Args:
            group_id: Идентификатор группы Telegram

        Returns:
            Список участников группы
        """
        try:
            result = await self.session.execute(
                select(GroupMember).where(GroupMember.group_id == group_id)
            )
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения участников группы {group_id}: {e}")
            return []

    async def get_member_groups(self, member_id: int) -> Sequence[GroupMember]:
        """
        Получить все группы участника

        Args:
            member_id: Идентификатор участника Telegram

        Returns:
            Список групп участника
        """
        try:
            result = await self.session.execute(
                select(GroupMember).where(GroupMember.member_id == member_id)
            )
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения групп участника {member_id}: {e}")
            return []

    async def is_member(self, group_id: int, member_id: int) -> bool:
        """
        Проверить является ли пользователь участником группы

        Args:
            group_id: Идентификатор группы Telegram
            member_id: Идентификатор участника Telegram

        Returns:
            True если является участником, False в противном случае
        """
        try:
            result = await self.session.execute(
                select(GroupMember).where(
                    GroupMember.group_id == group_id, GroupMember.member_id == member_id
                )
            )
            return result.scalar_one_or_none() is not None
        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка проверки участия {member_id} в группе {group_id}: {e}"
            )
            return False

    async def get_member_count(self, group_id: int) -> int:
        """
        Получить количество участников группы

        Args:
            group_id: Идентификатор группы Telegram

        Returns:
            Количество участников группы
        """
        try:
            result = await self.session.execute(
                select(GroupMember).where(GroupMember.group_id == group_id)
            )
            return len(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка подсчета участников группы {group_id}: {e}")
            return 0

    async def remove_all_members(self, group_id: int) -> bool:
        """
        Удалить всех участников из группы

        Args:
            group_id: Идентификатор группы Telegram

        Returns:
            True если участники были удалены, False в случае ошибки
        """
        try:
            await self.session.execute(
                delete(GroupMember).where(GroupMember.group_id == group_id)
            )
            await self.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка удаления всех участников группы {group_id}: {e}")
            await self.session.rollback()
            return False

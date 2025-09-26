import logging
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import delete, select, update
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

    async def mute_member(
        self, group_id: int, member_id: int, unmute_at: Optional[datetime] = None
    ) -> bool:
        """
        Заглушить участника в группе

        Args:
            group_id: Идентификатор группы Telegram
            member_id: Идентификатор участника Telegram
            unmute_at: Время автоматического размута (если указан временный мьют)

        Returns:
            True если участник был заглушен, False в случае ошибки
        """
        try:
            result = await self.session.execute(
                update(GroupMember)
                .where(
                    GroupMember.group_id == group_id, GroupMember.member_id == member_id
                )
                .values(is_muted=True, unmute_at=unmute_at)
            )
            await self.session.commit()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка заглушения участника {member_id} в группе {group_id}: {e}"
            )
            await self.session.rollback()
            return False

    async def unmute_member(self, group_id: int, member_id: int) -> bool:
        """
        Разглушить участника в группе

        Args:
            group_id: Идентификатор группы Telegram
            member_id: Идентификатор участника Telegram

        Returns:
            True если участник был разглушен, False в случае ошибки
        """
        try:
            result = await self.session.execute(
                update(GroupMember)
                .where(
                    GroupMember.group_id == group_id, GroupMember.member_id == member_id
                )
                .values(is_muted=False, unmute_at=None)
            )
            await self.session.commit()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка разглушения участника {member_id} в группе {group_id}: {e}"
            )
            await self.session.rollback()
            return False

    async def is_member_muted(self, group_id: int, member_id: int) -> bool:
        """
        Проверить заглушен ли участник в группе

        Args:
            group_id: Идентификатор группы Telegram
            member_id: Идентификатор участника Telegram

        Returns:
            True если участник заглушен, False в противном случае
        """
        try:
            result = await self.session.execute(
                select(GroupMember.is_muted, GroupMember.unmute_at).where(
                    GroupMember.group_id == group_id, GroupMember.member_id == member_id
                )
            )
            member_data = result.first()

            if member_data is None:
                return False

            is_muted, unmute_at = member_data

            # Если пользователь не заглушен
            if not is_muted:
                return False

            # Если заглушен навсегда (unmute_at is None)
            if unmute_at is None:
                return True

            # Если заглушен временно, проверяем время
            current_time = datetime.now()
            if current_time >= unmute_at:
                # Время мьюта истекло, автоматически размучиваем
                await self.unmute_member(group_id, member_id)
                return False

            return True
        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка проверки заглушения участника {member_id} в группе {group_id}: {e}"
            )
            return False

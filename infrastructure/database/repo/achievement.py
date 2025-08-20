from typing import Optional

from sqlalchemy import select

from infrastructure.database.models.achievement import Achievement
from infrastructure.database.repo.base import BaseRepo


class AchievementsRepo(BaseRepo):
    async def get_achievements(self):
        """
        Получаем полный список достижений
        """

        select_stmt = select(Achievement)

        result = await self.session.execute(select_stmt)
        awards = result.scalars().all()

        return list(awards)

    async def get_achievement(self, achievement_id: int) -> Optional[Achievement]:
        """
        Получение информации о достижении по его идентификатору

        Args:
            achievement_id: Уникальный идентификатор достижения в таблице achievements
        """

        select_stmt = select(Achievement).where(Achievement.id == achievement_id)
        result = await self.session.execute(select_stmt)

        return result.scalar_one()

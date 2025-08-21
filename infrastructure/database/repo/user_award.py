from sqlalchemy import func, select

from infrastructure.database.models import Award
from infrastructure.database.models.user_achievement import UserAchievement
from infrastructure.database.models.user_award import UserAward
from infrastructure.database.repo.base import BaseRepo


class UserAwardsRepo(BaseRepo):
    async def get_user_awards(self, user_id: int) -> list[UserAchievement]:
        """
        Получаем полный список наград пользователя
        """

        select_stmt = select(UserAchievement).where(UserAchievement.user_id == user_id)

        result = await self.session.execute(select_stmt)
        achievements = result.scalars().all()

        return list(achievements)

    async def get_user_awards_sum(self, user_id: int) -> int:
        """
        Получаем сумму наград пользователя через JOIN с таблицей наград
        """
        select_stmt = (
            select(func.sum(Award.cost))
            .select_from(UserAward)
            .join(Award, Award.id == UserAward.award_id)
            .where(UserAward.user_id == user_id)
        )

        result = await self.session.execute(select_stmt)
        total = result.scalar()

        return total or 0  # Если награда не найдена - возвращаем 0

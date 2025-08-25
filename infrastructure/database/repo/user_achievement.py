from sqlalchemy import select

from infrastructure.database.models.achievement import Achievement
from infrastructure.database.models.user_achievement import UserAchievement
from infrastructure.database.repo.base import BaseRepo


class UserAchievementsRepo(BaseRepo):
    async def get_user_achievements(self, user_id: int) -> list[UserAchievement]:
        """
        Получаем полный список достижений пользователя
        """

        select_stmt = select(UserAchievement).where(UserAchievement.user_id == user_id)

        result = await self.session.execute(select_stmt)
        achievements = result.scalars().all()

        return list(achievements)

    async def get_user_achievements_sum(self, user_id: int) -> int:
        """
        Получаем сумму наград пользователя через JOIN с таблицей достижений
        """
        from sqlalchemy import func

        select_stmt = (
            select(func.sum(Achievement.reward))
            .select_from(UserAchievement)
            .join(Achievement, UserAchievement.achievement_id == Achievement.id)
            .where(UserAchievement.user_id == user_id)
        )

        result = await self.session.execute(select_stmt)
        total = result.scalar()

        return total or 0  # Если достижение не найдено - возвращаем 0

    async def get_most_frequent_achievement(
        self, user_id: int
    ) -> tuple[str, int] | None:
        """
        Получаем самое частое достижение пользователя

        Returns:
            tuple[str, int]: (название достижения, количество получений) или None если нет достижений
        """
        from sqlalchemy import func

        select_stmt = (
            select(
                Achievement.name,
                func.count(UserAchievement.achievement_id).label("count"),
            )
            .select_from(UserAchievement)
            .join(Achievement, UserAchievement.achievement_id == Achievement.id)
            .where(UserAchievement.user_id == user_id)
            .group_by(UserAchievement.achievement_id, Achievement.name)
            .order_by(func.count(UserAchievement.achievement_id).desc())
            .limit(1)
        )

        result = await self.session.execute(select_stmt)
        most_frequent = result.first()

        if not most_frequent:
            return None

        return (most_frequent.name, most_frequent.count)

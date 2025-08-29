import logging

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models import User
from infrastructure.database.models.STP.achievement import Achievement
from infrastructure.database.models.STP.user_achievement import UserAchievement
from infrastructure.database.repo.base import BaseRepo

logger = logging.getLogger(__name__)


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

        return most_frequent.name, most_frequent.count

    async def get_group_achievements_statistics(self, head_name: str) -> dict:
        """
        Получить статистику достижений для группы руководителя

        Args:
            head_name: Имя руководителя

        Returns:
            Словарь со статистикой достижений группы
        """
        try:
            # Получаем все достижения сотрудников группы
            query = (
                select(
                    Achievement.name,
                    func.count(UserAchievement.achievement_id).label("count"),
                    func.sum(Achievement.reward).label("total_points"),
                )
                .select_from(User)
                .join(UserAchievement, User.user_id == UserAchievement.user_id)
                .join(Achievement, UserAchievement.achievement_id == Achievement.id)
                .where(User.head == head_name)
                .group_by(Achievement.name)
                .order_by(func.count(UserAchievement.achievement_id).desc())
            )

            result = await self.session.execute(query)
            achievements_stats = result.all()

            total_achievements = sum(stat.count for stat in achievements_stats)
            total_points = sum(stat.total_points for stat in achievements_stats)
            most_popular = achievements_stats[0] if achievements_stats else None

            return {
                "total_achievements": total_achievements,
                "total_points": total_points,
                "most_popular": most_popular,
                "details": achievements_stats,
            }

        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка получения статистики достижений для группы {head_name}: {e}"
            )
            return {
                "total_achievements": 0,
                "total_points": 0,
                "most_popular": None,
                "details": [],
            }

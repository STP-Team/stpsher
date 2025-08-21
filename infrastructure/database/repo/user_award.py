from dataclasses import dataclass

from sqlalchemy import func, select

from infrastructure.database.models import Award
from infrastructure.database.models.user_award import UserAward
from infrastructure.database.repo.base import BaseRepo


@dataclass
class UserAwardWithDetails:
    user_award: UserAward
    award_info: Award

    @property
    def max_usages(self) -> int:
        return self.award_info.count

    @property
    def current_usages(self) -> int:
        return self.user_award.usage_count


class UserAwardsRepo(BaseRepo):
    async def get_user_awards(self, user_id: int) -> list[UserAward]:
        """
        Получаем полный список наград пользователя
        """
        select_stmt = select(UserAward).where(UserAward.user_id == user_id)
        result = await self.session.execute(select_stmt)
        awards = result.scalars().all()
        return list(awards)

    async def get_user_awards_with_details(
        self, user_id: int
    ) -> list[UserAwardWithDetails]:
        """
        Получаем полный список наград пользователя с информацией о каждой награде
        """
        from infrastructure.database.models import Award

        select_stmt = (
            select(UserAward, Award)
            .join(Award, UserAward.award_id == Award.id)
            .where(UserAward.user_id == user_id)
        )

        result = await self.session.execute(select_stmt)
        awards_with_details = result.all()

        return [
            UserAwardWithDetails(user_award=user_award, award_info=award)
            for user_award, award in awards_with_details
        ]

    async def get_user_award_detail(
        self, user_award_id: int
    ) -> UserAwardWithDetails | None:
        """
        Получаем детальную информацию о конкретной награде пользователя
        """
        select_stmt = (
            select(UserAward, Award)
            .join(Award, UserAward.award_id == Award.id)
            .where(UserAward.id == user_award_id)
        )

        result = await self.session.execute(select_stmt)
        award_detail = result.first()

        if not award_detail:
            return None

        user_award, award = award_detail
        return UserAwardWithDetails(user_award=user_award, award_info=award)

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

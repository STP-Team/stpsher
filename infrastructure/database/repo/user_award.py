from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TypedDict, Unpack

from sqlalchemy import func, select

from infrastructure.database.models import Award
from infrastructure.database.models.user_award import UserAward
from infrastructure.database.repo.base import BaseRepo


class UserAwardParams(TypedDict, total=False):
    """Доступные параметры для обновления награды пользователя в таблице users_awards."""

    award_id: int | None
    comment: str | None
    usage_count: str | None
    bought_at: datetime | None
    updated_at: datetime | None
    updated_by_user_id: int | None
    status: str


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
    async def create_user_award(
        self, user_id: int, award_id: int, status: str = "waiting", comment: str = None
    ) -> UserAward:
        """
        Создаем новую награду для пользователя

        Args:
            user_id: ID пользователя Telegram
            award_id: ID награды из таблицы awards
            status: Статус награды (по умолчанию "waiting")
            comment: Комментарий к награде (опционально)

        Returns:
            UserAward: Созданная награда пользователя
        """
        from datetime import datetime

        user_award = UserAward(
            user_id=user_id,
            award_id=award_id,
            comment=comment,
            usage_count=0,
            bought_at=datetime.now(),
            status=status,
        )

        self.session.add(user_award)
        await self.session.commit()
        await self.session.refresh(user_award)

        return user_award

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
            .order_by(UserAward.bought_at.desc())
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

    async def get_waiting_awards_for_activation(
        self, manager_role: int
    ) -> list[UserAwardWithDetails]:
        """
        Получаем список наград ожидающих активации
        Фильтруем по статусу "waiting" и manager_role
        """
        from infrastructure.database.models import Award, User

        select_stmt = (
            select(UserAward, Award, User)
            .join(Award, UserAward.award_id == Award.id)
            .join(User, UserAward.user_id == User.user_id)
            .where(UserAward.status == "waiting", Award.manager_role == manager_role)
            .order_by(
                UserAward.bought_at.desc()
            )  # Сортируем по дате покупки (новые сначала)
        )

        result = await self.session.execute(select_stmt)
        awards_with_details = result.all()

        return [
            UserAwardWithDetails(user_award=user_award, award_info=award)
            for user_award, award, user in awards_with_details
        ]

    async def update_award(
        self,
        award_id: int = None,
        **kwargs: Unpack[UserAwardParams],
    ) -> Optional[Award]:
        select_stmt = select(UserAward).where(UserAward.id == award_id)

        result = await self.session.execute(select_stmt)
        award: Award | None = result.scalar_one_or_none()

        # Если пользователь существует - обновляем его
        if award:
            for key, value in kwargs.items():
                setattr(award, key, value)
            await self.session.commit()

        return award

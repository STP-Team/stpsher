import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TypedDict, Unpack

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models import Award, User
from infrastructure.database.models.STP.awards_usage import AwardUsage
from infrastructure.database.repo.base import BaseRepo

logger = logging.getLogger(__name__)


class AwardUsageParams(TypedDict, total=False):
    """Доступные параметры для обновления награды пользователя в таблице users_awards."""

    award_id: int | None
    comment: str | None
    usage_count: str | None
    bought_at: datetime | None
    updated_at: datetime | None
    updated_by_user_id: int | None
    status: str


@dataclass
class AwardUsageWithDetails:
    user_award: AwardUsage
    award_info: Award

    @property
    def max_usages(self) -> int:
        return self.award_info.count

    @property
    def current_usages(self) -> int:
        return self.user_award.usage_count


class AwardUsageRepo(BaseRepo):
    async def create_user_award(
        self, user_id: int, award_id: int, status: str = "stored", comment: str = None
    ) -> AwardUsage:
        """
        Создаем новую награду для пользователя

        Args:
            user_id: ID пользователя Telegram
            award_id: ID награды из таблицы awards
            status: Статус награды (по умолчанию "stored")
            comment: Комментарий к награде (опционально)

        Returns:
            AwardUsage: Созданная награда пользователя
        """
        from datetime import datetime

        user_award = AwardUsage(
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

    async def get_user_awards(self, user_id: int) -> list[AwardUsage]:
        """
        Получаем полный список наград пользователя
        """
        select_stmt = select(AwardUsage).where(AwardUsage.user_id == user_id)
        result = await self.session.execute(select_stmt)
        awards = result.scalars().all()
        return list(awards)

    async def get_user_awards_with_details(
        self, user_id: int
    ) -> list[AwardUsageWithDetails]:
        """
        Получаем полный список наград пользователя с информацией о каждой награде
        """
        from infrastructure.database.models import Award

        select_stmt = (
            select(AwardUsage, Award)
            .join(Award, AwardUsage.award_id == Award.id)
            .where(AwardUsage.user_id == user_id)
            .order_by(AwardUsage.bought_at.desc())
        )

        result = await self.session.execute(select_stmt)
        awards_with_details = result.all()

        return [
            AwardUsageWithDetails(user_award=user_award, award_info=award)
            for user_award, award in awards_with_details
        ]

    async def get_user_award_detail(
        self, user_award_id: int
    ) -> AwardUsageWithDetails | None:
        """
        Получаем детальную информацию о конкретной награде пользователя
        """
        select_stmt = (
            select(AwardUsage, Award)
            .join(Award, AwardUsage.award_id == Award.id)
            .where(AwardUsage.id == user_award_id)
        )

        result = await self.session.execute(select_stmt)
        award_detail = result.first()

        if not award_detail:
            return None

        user_award, award = award_detail
        return AwardUsageWithDetails(user_award=user_award, award_info=award)

    async def get_user_awards_sum(self, user_id: int) -> int:
        """
        Получаем сумму наград пользователя через JOIN с таблицей наград
        """
        select_stmt = (
            select(func.sum(Award.cost))
            .select_from(AwardUsage)
            .join(Award, Award.id == AwardUsage.award_id)
            .where(AwardUsage.user_id == user_id)
        )

        result = await self.session.execute(select_stmt)
        total = result.scalar()

        return total or 0  # Если награда не найдена - возвращаем 0

    async def get_review_awards_for_activation(
        self, manager_role: int, division: str = None
    ) -> list[AwardUsageWithDetails]:
        """
        Получаем список наград ожидающих активации
        Фильтруем по статусу "review" и manager_role
        Опционально фильтруем по division пользователей
        """
        from infrastructure.database.models import Award, User

        select_stmt = (
            select(AwardUsage, Award, User)
            .join(Award, AwardUsage.award_id == Award.id)
            .join(User, AwardUsage.user_id == User.user_id)
            .where(AwardUsage.status == "review", Award.manager_role == manager_role)
        )

        # Добавляем фильтр по division если указан
        if division:
            select_stmt = select_stmt.where(User.division == division)

        select_stmt = select_stmt.order_by(
            AwardUsage.bought_at.asc()
        )  # Сортируем по дате покупки (сначала старые)

        result = await self.session.execute(select_stmt)
        awards_with_details = result.all()

        return [
            AwardUsageWithDetails(user_award=user_award, award_info=award)
            for user_award, award, user in awards_with_details
        ]

    async def update_award(
        self,
        award_id: int = None,
        **kwargs: Unpack[AwardUsageParams],
    ) -> Optional[Award]:
        select_stmt = select(AwardUsage).where(AwardUsage.id == award_id)

        result = await self.session.execute(select_stmt)
        award: Award | None = result.scalar_one_or_none()

        # Если пользователь существует - обновляем его
        if award:
            for key, value in kwargs.items():
                setattr(award, key, value)
            await self.session.commit()

        return award

    async def use_award(self, user_award_id: int) -> bool:
        """
        User clicks 'Use Award' button - changes status from 'stored' to 'review'

        Returns:
            bool: True if successful, False if not available for use
        """
        select_stmt = select(AwardUsage).where(AwardUsage.id == user_award_id)
        result = await self.session.execute(select_stmt)
        user_award = result.scalar_one_or_none()

        if not user_award or user_award.status != "stored":
            return False

        # Get award info to check usage limits
        award_info = await self.session.get(Award, user_award.award_id)
        if user_award.usage_count >= award_info.count:
            return False

        user_award.status = "review"
        user_award.updated_at = datetime.now()

        await self.session.commit()
        return True

    async def approve_award_usage(
        self, user_award_id: int, updated_by_user_id: int
    ) -> bool:
        """
        Manager approves award usage - increments usage_count and sets status back to 'stored' or 'used_up'
        """
        # Get the user award first
        user_award = await self.session.get(AwardUsage, user_award_id)
        if not user_award:
            return False

        # Get the award info
        award_info = await self.session.get(Award, user_award.award_id)
        if not award_info:
            return False

        # Increment usage count
        user_award.usage_count += 1
        user_award.updated_at = datetime.now()
        user_award.updated_by_user_id = updated_by_user_id

        # Set status based on remaining uses
        if user_award.usage_count >= award_info.count:
            user_award.status = "used_up"
        else:
            user_award.status = "stored"

        await self.session.commit()
        return True

    async def reject_award_usage(
        self, user_award_id: int, updated_by_user_id: int
    ) -> bool:
        """
        Отмена использования награды - возвращает статус награды на 'stored' или 'used_up'
        """
        # Get the user award first
        user_award = await self.session.get(AwardUsage, user_award_id)
        if not user_award:
            return False

        # Get the award info
        award_info = await self.session.get(Award, user_award.award_id)
        if not award_info:
            return False

        user_award.updated_at = datetime.now()
        user_award.updated_by_user_id = updated_by_user_id

        # Set status based on remaining uses
        if user_award.usage_count >= award_info.count:
            user_award.status = "used_up"
        else:
            user_award.status = "stored"

        await self.session.commit()
        return True

    async def delete_user_award(self, user_award_id: int) -> bool:
        """
        Удаляет запись о награде пользователя из БД (для продажи)

        Args:
            user_award_id: ID записи в таблице user_awards

        Returns:
            bool: True if successful, False if award not found
        """
        select_stmt = select(AwardUsage).where(AwardUsage.id == user_award_id)
        result = await self.session.execute(select_stmt)
        user_award = result.scalar_one_or_none()

        if not user_award:
            return False

        # Проверяем, что награду можно удалить (только со статусом "stored" и usage_count = 0)
        if user_award.status != "stored" or user_award.usage_count > 0:
            return False

        await self.session.delete(user_award)
        await self.session.commit()

        return True

    async def get_most_used_award(self, user_id: int) -> tuple[str, int] | None:
        """
        Получаем самую используемую награду пользователя

        Returns:
            tuple[str, int]: (название награды, количество использований) или None если нет наград
        """
        select_stmt = (
            select(Award.name, AwardUsage.usage_count)
            .select_from(AwardUsage)
            .join(Award, AwardUsage.award_id == Award.id)
            .where(AwardUsage.user_id == user_id)
            .order_by(AwardUsage.usage_count.desc())
            .limit(1)
        )

        result = await self.session.execute(select_stmt)
        most_used = result.first()

        if not most_used:
            return None

        return most_used.name, most_used.usage_count

    async def get_group_awards_statistics(self, head_name: str) -> dict:
        """
        Получить статистику наград для группы руководителя

        Args:
            head_name: Имя руководителя

        Returns:
            Словарь со статистикой наград группы
        """
        from sqlalchemy import func

        from infrastructure.database.models import Award
        from infrastructure.database.models.STP.awards_usage import AwardUsage

        try:
            # Получаем все награды сотрудников группы
            query = (
                select(
                    Award.name,
                    func.sum(AwardUsage.usage_count).label("total_usage"),
                    func.count(AwardUsage.award_id).label("purchase_count"),
                )
                .select_from(User)
                .join(AwardUsage, User.user_id == AwardUsage.user_id)
                .join(Award, AwardUsage.award_id == Award.id)
                .where(User.head == head_name)
                .group_by(Award.name)
                .order_by(func.sum(AwardUsage.usage_count).desc())
            )

            result = await self.session.execute(query)
            awards_stats = result.all()

            total_usage = sum(stat.total_usage for stat in awards_stats)
            total_purchases = sum(stat.purchase_count for stat in awards_stats)
            most_popular = awards_stats[0] if awards_stats else None

            return {
                "total_usage": total_usage,
                "total_purchases": total_purchases,
                "most_popular": most_popular,
                "details": awards_stats,
            }

        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка получения статистики наград для группы {head_name}: {e}"
            )
            return {
                "total_usage": 0,
                "total_purchases": 0,
                "most_popular": None,
                "details": [],
            }

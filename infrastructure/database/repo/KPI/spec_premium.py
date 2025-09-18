import logging
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models.KPI.spec_premium import SpecPremium
from infrastructure.database.repo.base import BaseRepo

logger = logging.getLogger(__name__)


class SpecPremiumRepo(BaseRepo):
    async def get_premium(
        self,
        fullname: str,
    ) -> Optional[SpecPremium]:
        """
        Поиск показателей премиума специалиста в БД по ФИО

        Args:
            fullname: ФИО специалиста в БД

        Returns:
            Объект SpecPremium или ничего
        """
        query = select(SpecPremium).where(SpecPremium.fullname == fullname)

        try:
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения показателей премиума специалиста: {e}")
            return None

    async def get_kpi_by_names(
        self,
        fullnames: list[str],
    ) -> Sequence[SpecPremium]:
        """
        Поиск показателей премиума специалистов в БД по списку ФИО

        Args:
            fullnames: Список ФИО специалистов в БД

        Returns:
            Список объектов SpecPremium
        """
        if not fullnames:
            return []

        query = select(SpecPremium).where(SpecPremium.fullname.in_(fullnames))

        try:
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка получения показателей премиума специалистов: {e}"
            )
            return []

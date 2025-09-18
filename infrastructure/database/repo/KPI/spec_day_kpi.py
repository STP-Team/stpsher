import logging
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models.KPI.spec_kpi import SpecDayKPI
from infrastructure.database.repo.base import BaseRepo

logger = logging.getLogger(__name__)


class SpecDayKPIRepo(BaseRepo):
    async def get_kpi(
        self,
        fullname: str,
    ) -> Optional[SpecDayKPI]:
        """
        Поиск показателей специалиста за день в БД по ФИО

        Args:
            fullname: ФИО специалиста в БД

        Returns:
            Объект SpecDayKPI или ничего
        """
        query = select(SpecDayKPI).where(SpecDayKPI.fullname == fullname)

        try:
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения дневных показателей специалиста: {e}")
            return None

    async def get_kpi_by_names(
        self,
        fullnames: list[str],
    ) -> Sequence[SpecDayKPI]:
        """
        Поиск показателей специалистов за день в БД по списку ФИО

        Args:
            fullnames: Список ФИО специалистов в БД

        Returns:
            Список объектов SpecDayKPI
        """
        if not fullnames:
            return []

        query = select(SpecDayKPI).where(SpecDayKPI.fullname.in_(fullnames))

        try:
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения дневных показателей специалистов: {e}")
            return []

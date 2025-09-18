import logging
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models.KPI.spec_kpi import SpecWeekKPI
from infrastructure.database.repo.base import BaseRepo

logger = logging.getLogger(__name__)


class SpecWeekKPIRepo(BaseRepo):
    async def get_kpi(
        self,
        fullname: str,
    ) -> Optional[SpecWeekKPI]:
        """
        Поиск показателей специалиста за неделю в БД по ФИО

        Args:
            fullname: ФИО специалиста в БД

        Returns:
            Объект SpecWeekKPI или ничего
        """
        query = select(SpecWeekKPI).where(SpecWeekKPI.fullname == fullname)

        try:
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка получения недельных показателей специалиста: {e}"
            )
            return None

    async def get_kpi_by_names(
        self,
        fullnames: list[str],
    ) -> Sequence[SpecWeekKPI]:
        """
        Поиск показателей специалистов за неделю в БД по списку ФИО

        Args:
            fullnames: Список ФИО специалистов в БД

        Returns:
            Список объектов SpecWeekKPI
        """
        if not fullnames:
            return []

        query = select(SpecWeekKPI).where(SpecWeekKPI.fullname.in_(fullnames))

        try:
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка получения недельных показателей специалистов: {e}"
            )
            return []

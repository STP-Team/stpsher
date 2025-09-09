import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models.KPI.spec_kpi import SpecMonthKPI
from infrastructure.database.repo.base import BaseRepo

logger = logging.getLogger(__name__)


class SpecMonthKPIRepo(BaseRepo):
    async def get_kpi(
        self,
        fullname: str,
    ) -> Optional[SpecMonthKPI]:
        """
        Поиск показателей специалиста за месяц в БД по ФИО

        Args:
            fullname: ФИО специалиста в БД

        Returns:
            Объект SpecMonthKPI или ничего
        """
        query = select(SpecMonthKPI).where(SpecMonthKPI.fullname == fullname)

        try:
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения месячных показателей специалиста: {e}")
            return None

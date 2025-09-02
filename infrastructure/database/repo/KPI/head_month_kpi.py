import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models.KPI.head_kpi import HeadMonthKPI
from infrastructure.database.repo.base import BaseRepo

logger = logging.getLogger(__name__)


class HeadMonthKPIRepo(BaseRepo):
    async def get_kpi(
        self,
        fullname: str,
    ) -> Optional[HeadMonthKPI]:
        """
        Поиск показателей руководителя в БД по ФИО

        Args:
            fullname: ФИО руководителя в БД

        Returns:
            Объект HeadMonthKPI или ничего
        """
        query = select(HeadMonthKPI).where(HeadMonthKPI.fullname == fullname)

        try:
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения показателей руководителя: {e}")
            return None

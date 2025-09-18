import logging
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models.KPI.head_premium import HeadPremium
from infrastructure.database.repo.base import BaseRepo

logger = logging.getLogger(__name__)


class HeadPremiumRepo(BaseRepo):
    async def get_premium(
        self,
        fullname: str,
    ) -> Optional[HeadPremium]:
        """
        Поиск показателей премиума руководителя в БД по ФИО

        Args:
            fullname: ФИО руководителя в БД

        Returns:
            Объект HeadPremium или ничего
        """
        query = select(HeadPremium).where(HeadPremium.fullname == fullname)

        try:
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка получения показателей премиума руководителя: {e}"
            )
            return None

    async def get_kpi_by_names(
        self,
        fullnames: list[str],
    ) -> Sequence[HeadPremium]:
        """
        Поиск показателей премиума руководителей в БД по списку ФИО

        Args:
            fullnames: Список ФИО руководителей в БД

        Returns:
            Список объектов HeadPremium
        """
        if not fullnames:
            return []

        query = select(HeadPremium).where(HeadPremium.fullname.in_(fullnames))

        try:
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка получения показателей премиума руководителей: {e}"
            )
            return []

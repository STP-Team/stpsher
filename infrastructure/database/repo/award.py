from typing import List, Optional

from sqlalchemy import select, and_

from infrastructure.database.models import Award
from infrastructure.database.repo.base import BaseRepo


class AwardsRepo(BaseRepo):
    async def get_awards(self, division: str = None):
        """
        Получаем полный список наград
        """

        if division:
            select_stmt = select(Award).where(Award.division == division)
        else:
            select_stmt = select(Award)

        result = await self.session.execute(select_stmt)
        awards = result.scalars().all()

        return list(awards)

    async def get_award(self, award_id: int) -> Optional[Award]:
        """
        Получение информации о награде по ее идентификатору

        Args:
            award_id: Уникальный идентификатор награды в таблице awards
        """

        select_stmt = select(Award).where(Award.id == award_id)
        result = await self.session.execute(select_stmt)

        return result.scalar_one()

    async def get_available_awards(self, user_balance: int) -> List[Award]:
        """
        Получаем список наград, у которых:
        - стоимость награды меньше или равна кол-ву очков пользователя
        """

        # Получаем список наград, подходящих под критерии
        select_stmt = select(Award).where(and_(Award.cost <= user_balance))

        result = await self.session.execute(select_stmt)
        awards = result.scalars().all()

        return list(awards)

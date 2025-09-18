from typing import List, Optional

from sqlalchemy import and_, select

from infrastructure.database.models import Product
from infrastructure.database.repo.base import BaseRepo


class ProductsRepo(BaseRepo):
    async def get_products(self, division: str = None):
        """
        Получаем полный список предметов
        """

        if division:
            select_stmt = select(Product).where(Product.division == division)
        else:
            select_stmt = select(Product)

        result = await self.session.execute(select_stmt)
        products = result.scalars().all()

        return list(products)

    async def get_product(self, product_id: int) -> Optional[Product]:
        """
        Получение информации о предмете по ег идентификатору

        Args:
            product_id: Уникальный идентификатор предмета в таблице products
        """

        select_stmt = select(Product).where(Product.id == product_id)
        result = await self.session.execute(select_stmt)

        return result.scalar_one()

    async def get_available_products(
        self, user_balance: int, division: str
    ) -> List[Product]:
        """
        Получаем список предметов, у которых:
        - стоимость предмета меньше или равна кол-ву баллов пользователя
        """

        # Получаем список предметов, подходящих под критерии
        select_stmt = select(Product).where(
            and_(Product.cost <= user_balance), Product.division == division
        )

        result = await self.session.execute(select_stmt)
        products = result.scalars().all()

        return list(products)

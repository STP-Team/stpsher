import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TypedDict, Unpack

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models import Employee, Product
from infrastructure.database.models.STP.purchase import Purchase
from infrastructure.database.repo.base import BaseRepo

logger = logging.getLogger(__name__)


class PurchaseParams(TypedDict, total=False):
    """Доступные параметры для обновления покупки пользователя в таблице purchases."""

    product_id: int | None
    comment: str | None
    usage_count: str | None
    bought_at: datetime | None
    updated_at: datetime | None
    updated_by_user_id: int | None
    status: str


@dataclass
class PurchaseDetailedParams:
    user_purchase: Purchase
    product_info: Product

    @property
    def max_usages(self) -> int:
        return self.product_info.count

    @property
    def current_usages(self) -> int:
        return self.user_purchase.usage_count


class PurchaseRepo(BaseRepo):
    async def add_purchase(
        self, user_id: int, product_id: int, status: str = "stored", comment: str = None
    ) -> Purchase:
        """
        Создаем новую покупку для пользователя

        Args:
            user_id: ID пользователя Telegram
            product_id: ID предмета из таблицы products
            status: Статус покупки (по умолчанию "stored")
            comment: Комментарий к покупке (опционально)

        Returns:
            Purchase: Созданная покупка пользователя
        """
        from datetime import datetime

        user_purchase = Purchase(
            user_id=user_id,
            product_id=product_id,
            comment=comment,
            usage_count=0,
            bought_at=datetime.now(),
            status=status,
        )

        self.session.add(user_purchase)
        await self.session.commit()
        await self.session.refresh(user_purchase)

        return user_purchase

    async def get_user_purchases(self, user_id: int) -> list[Purchase]:
        """
        Получаем полный список покупок пользователя
        """
        select_stmt = select(Purchase).where(Purchase.user_id == user_id)
        result = await self.session.execute(select_stmt)
        purchases = result.scalars().all()
        return list(purchases)

    async def get_user_purchases_with_details(
        self, user_id: int
    ) -> list[PurchaseDetailedParams]:
        """
        Получаем полный список покупок пользователя с информацией о каждой покупке
        """
        from infrastructure.database.models import Product

        select_stmt = (
            select(Purchase, Product)
            .join(Product, Purchase.product_id == Product.id)
            .where(Purchase.user_id == user_id)
            .order_by(Purchase.bought_at.desc())
        )

        result = await self.session.execute(select_stmt)
        purchases_with_details = result.all()

        return [
            PurchaseDetailedParams(user_purchase=purchase, product_info=product)
            for purchase, product in purchases_with_details
        ]

    async def get_purchase_details(
        self, user_purchase_id: int
    ) -> PurchaseDetailedParams | None:
        """
        Получаем детальную информацию о конкретной покупке пользователя
        """
        select_stmt = (
            select(Purchase, Product)
            .join(Product, Purchase.product_id == Product.id)
            .where(Purchase.id == user_purchase_id)
        )

        result = await self.session.execute(select_stmt)
        purchase_details = result.first()

        if not purchase_details:
            return None

        purchase, product = purchase_details
        return PurchaseDetailedParams(user_purchase=purchase, product_info=product)

    async def get_user_purchases_sum(self, user_id: int) -> int:
        """
        Получаем сумму покупок пользователя через JOIN с таблицей предметов products
        """
        select_stmt = (
            select(func.sum(Product.cost))
            .select_from(Purchase)
            .join(Product, Product.id == Purchase.product_id)
            .where(Purchase.user_id == user_id)
        )

        result = await self.session.execute(select_stmt)
        total = result.scalar()

        return total or 0  # Если покупка не найдена - возвращаем 0

    async def get_review_purchases_for_activation(
        self, manager_role: int, division: str = None
    ) -> list[PurchaseDetailedParams]:
        """
        Получаем список покупок, ожидающих активации
        Фильтруем по статусу "review" и manager_role
        Опционально фильтруем по division пользователей
        """
        from infrastructure.database.models import Employee, Product

        select_stmt = (
            select(Purchase, Product, Employee)
            .join(Product, Purchase.product_id == Product.id)
            .join(Employee, Purchase.user_id == Employee.user_id)
            .where(Purchase.status == "review", Product.manager_role == manager_role)
        )

        # Добавляем фильтр по division если указан
        if division:
            select_stmt = select_stmt.where(Employee.division == division)

        select_stmt = select_stmt.order_by(
            Purchase.bought_at.asc()
        )  # Сортируем по дате покупки (сначала старые)

        result = await self.session.execute(select_stmt)
        purchases_with_details = result.all()

        return [
            PurchaseDetailedParams(user_purchase=purchase, product_info=product)
            for purchase, product, user in purchases_with_details
        ]

    async def update_purchase(
        self,
        purchase_id: int = None,
        **kwargs: Unpack[PurchaseParams],
    ) -> Optional[Product]:
        select_stmt = select(Purchase).where(Purchase.id == purchase_id)

        result = await self.session.execute(select_stmt)
        product: Product | None = result.scalar_one_or_none()

        # Если пользователь существует - обновляем его
        if product:
            for key, value in kwargs.items():
                setattr(product, key, value)
            await self.session.commit()

        return product

    async def use_purchase(self, purchase_id: int) -> bool:
        """
        User clicks 'Использовать' button - changes status from 'stored' to 'review'

        Returns:
            bool: True if successful, False if not available for use
        """
        select_stmt = select(Purchase).where(Purchase.id == purchase_id)
        result = await self.session.execute(select_stmt)
        purchase = result.scalar_one_or_none()

        if not purchase or purchase.status != "stored":
            return False

        # Get product info to check usage limits
        product_info = await self.session.get(Product, purchase.product_id)
        if purchase.usage_count >= product_info.count:
            return False

        purchase.status = "review"
        purchase.updated_at = datetime.now()

        await self.session.commit()
        return True

    async def approve_purchase_usage(
        self, purchase_id: int, updated_by_user_id: int
    ) -> bool:
        """
        Manager approves product usage - increments usage_count and sets status back to 'stored' or 'used_up'
        """
        # Get the user purchase first
        purchase = await self.session.get(Purchase, purchase_id)
        if not purchase:
            return False

        # Get the product info
        product_info = await self.session.get(Product, purchase.product_id)
        if not product_info:
            return False

        # Increment usage count
        purchase.usage_count += 1
        purchase.updated_at = datetime.now()
        purchase.updated_by_user_id = updated_by_user_id

        # Set status based on remaining uses
        if purchase.usage_count >= product_info.count:
            purchase.status = "used_up"
        else:
            purchase.status = "stored"

        await self.session.commit()
        return True

    async def reject_purchase_usage(
        self, purchase_id: int, updated_by_user_id: int
    ) -> bool:
        """
        Отмена использования предмета - возвращает статус покупки на 'stored' или 'used_up'
        """
        # Get the user purchase first
        purchase = await self.session.get(Purchase, purchase_id)
        if not purchase:
            return False

        # Get the product info
        product_info = await self.session.get(Product, purchase.product_id)
        if not product_info:
            return False

        purchase.updated_at = datetime.now()
        purchase.updated_by_user_id = updated_by_user_id

        # Set status based on remaining uses
        if purchase.usage_count >= product_info.count:
            purchase.status = "used_up"
        else:
            purchase.status = "stored"

        await self.session.commit()
        return True

    async def delete_user_purchase(self, purchase_id: int) -> bool:
        """
        Удаляет запись о покупке пользователя из БД (для возврата)

        Args:
            purchase_id: ID записи в таблице purchases

        Returns:
            bool: True если успешно, False если покупка не найдена
        """
        select_stmt = select(Purchase).where(Purchase.id == purchase_id)
        result = await self.session.execute(select_stmt)
        purchase = result.scalar_one_or_none()

        if not purchase:
            return False

        # Проверяем, что покупку можно удалить (только со статусом "stored" и usage_count = 0)
        if purchase.status != "stored" or purchase.usage_count > 0:
            return False

        await self.session.delete(purchase)
        await self.session.commit()

        return True

    async def get_most_bought_product(self, user_id: int) -> tuple[str, int] | None:
        """
        Получаем самый покупаемый предмет пользователя

        Returns:
            tuple[str, int]: (название предмета, количество использований) или None если нет предметов
        """
        select_stmt = (
            select(Product.name, Purchase.usage_count)
            .select_from(Purchase)
            .join(Product, Purchase.product_id == Product.id)
            .where(Purchase.user_id == user_id)
            .order_by(Purchase.usage_count.desc())
            .limit(1)
        )

        result = await self.session.execute(select_stmt)
        most_used = result.first()

        if not most_used:
            return None

        return most_used.name, most_used.usage_count

    async def get_group_purchases_stats(self, head_name: str) -> dict:
        """
        Получить статистику покупок для группы руководителя

        Args:
            head_name: Имя руководителя

        Returns:
            Словарь со статистикой покупок группы
        """
        from sqlalchemy import func

        from infrastructure.database.models import Product
        from infrastructure.database.models.STP.purchase import Purchase

        try:
            # Получаем все покупки сотрудников группы
            query = (
                select(
                    Product.name,
                    func.sum(Purchase.usage_count).label("total_usage"),
                    func.count(Purchase.product_id).label("purchase_count"),
                )
                .select_from(Employee)
                .join(Purchase, Employee.user_id == Purchase.user_id)
                .join(Product, Purchase.product_id == Product.id)
                .where(Employee.head == head_name)
                .group_by(Product.name)
                .order_by(func.sum(Purchase.usage_count).desc())
            )

            result = await self.session.execute(query)
            purchases_stats = result.all()

            total_usage = sum(stat.total_usage for stat in purchases_stats)
            total_purchases = sum(stat.purchase_count for stat in purchases_stats)
            most_popular = purchases_stats[0] if purchases_stats else None

            return {
                "total_usage": total_usage,
                "total_purchases": total_purchases,
                "most_popular": most_popular,
                "details": purchases_stats,
            }

        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка получения статистики покупок для группы {head_name}: {e}"
            )
            return {
                "total_usage": 0,
                "total_purchases": 0,
                "most_popular": None,
                "details": [],
            }

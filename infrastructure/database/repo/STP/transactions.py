import logging
from typing import Optional, Sequence, TypedDict, Unpack

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models.STP.transactions import Transaction
from infrastructure.database.repo.base import BaseRepo

logger = logging.getLogger(__name__)


class TransactionParams(TypedDict, total=False):
    """Доступные параметры для обновления транзакции."""

    user_id: int
    type: str
    source_id: Optional[int]
    source_type: str
    amount: int
    comment: Optional[str]
    created_by: Optional[int]


class TransactionRepo(BaseRepo):
    async def add_transaction(
        self,
        user_id: int,
        type: str,
        source_type: str,
        amount: int,
        source_id: Optional[int] = None,
        comment: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> Optional[Transaction]:
        """
        Добавить новую транзакцию в БД

        Args:
            user_id: Идентификатор пользователя
            type: Тип операции: 'earn' или 'spend'
            source_type: Источник транзакции: 'achievement', 'award', 'manual'
            amount: Количество баллов
            source_id: Идентификатор достижения или награды (опционально)
            comment: Комментарий (опционально)
            created_by: ID администратора, создавшего транзакцию (опционально)

        Returns:
            Объект Transaction или None в случае ошибки
        """
        try:
            transaction = Transaction(
                user_id=user_id,
                type=type,
                source_type=source_type,
                amount=amount,
                source_id=source_id,
                comment=comment,
                created_by=created_by,
            )

            self.session.add(transaction)
            await self.session.commit()
            await self.session.refresh(transaction)

            logger.info(
                f"[БД] Создана транзакция ID: {transaction.id} для пользователя {user_id}"
            )
            return transaction

        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка создания транзакции: {e}")
            await self.session.rollback()
            return None

    async def get_transaction(self, transaction_id: int) -> Optional[Transaction]:
        """
        Получить транзакцию по ID

        Args:
            transaction_id: Уникальный идентификатор транзакции

        Returns:
            Объект Transaction или None
        """
        try:
            result = await self.session.execute(
                select(Transaction).where(Transaction.id == transaction_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения транзакции {transaction_id}: {e}")
            return None

    async def get_user_transactions(
        self, user_id: int, only_achievements: bool = False
    ) -> Sequence[Transaction]:
        """
        Получить все транзакции пользователя

        Args:
            user_id: Идентификатор пользователя
            only_achievements: Если True, возвращать только транзакции-достижения

        Returns:
            Список транзакций пользователя
        """
        try:
            query = select(Transaction).where(Transaction.user_id == user_id)
            
            if only_achievements:
                query = query.where(Transaction.source_type == 'achievement')
            
            query = query.order_by(Transaction.created_at.desc())
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка получения транзакций пользователя {user_id}: {e}"
            )
            return []

    async def get_transactions(self) -> Sequence[Transaction]:
        """
        Получить все транзакции

        Returns:
            Список всех транзакций
        """
        try:
            result = await self.session.execute(
                select(Transaction).order_by(Transaction.created_at.desc())
            )
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения списка транзакций: {e}")
            return []

    async def update_transaction(
        self,
        transaction_id: int,
        **kwargs: Unpack[TransactionParams],
    ) -> Optional[Transaction]:
        """
        Обновить транзакцию

        Args:
            transaction_id: ID транзакции для обновления
            **kwargs: Параметры для обновления

        Returns:
            Обновленная транзакция или None
        """
        try:
            select_stmt = select(Transaction).where(Transaction.id == transaction_id)
            result = await self.session.execute(select_stmt)
            transaction: Transaction | None = result.scalar_one_or_none()

            if transaction:
                for key, value in kwargs.items():
                    setattr(transaction, key, value)
                await self.session.commit()
                logger.info(f"[БД] Транзакция {transaction_id} обновлена")

            return transaction
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка обновления транзакции {transaction_id}: {e}")
            await self.session.rollback()
            return None

    async def delete_transaction(self, transaction_id: int) -> bool:
        """
        Удалить транзакцию из БД

        Args:
            transaction_id: ID транзакции для удаления

        Returns:
            True если транзакция удалена, False в случае ошибки
        """
        try:
            result = await self.session.execute(
                select(Transaction).where(Transaction.id == transaction_id)
            )
            transaction = result.scalar_one_or_none()

            if transaction:
                await self.session.delete(transaction)
                await self.session.commit()
                logger.info(f"[БД] Транзакция {transaction_id} удалена")
                return True
            else:
                logger.warning(f"[БД] Транзакция {transaction_id} не найдена")
                return False

        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка удаления транзакции {transaction_id}: {e}")
            await self.session.rollback()
            return False

    async def get_user_balance(self, user_id: int) -> int:
        """
        Вычислить баланс пользователя (сумма всех транзакций)

        Args:
            user_id: Идентификатор пользователя

        Returns:
            Баланс пользователя
        """
        try:
            transactions = await self.get_user_transactions(user_id)
            balance = 0

            for transaction in transactions:
                if transaction.type == "earn":
                    balance += transaction.amount
                elif transaction.type == "spend":
                    balance -= transaction.amount

            return balance
        except Exception as e:
            logger.error(f"[БД] Ошибка вычисления баланса пользователя {user_id}: {e}")
            return 0

    async def get_user_achievements_sum(self, user_id: int) -> int:
        """
        Вычислить сумму баллов за достижения пользователя

        Args:
            user_id: Идентификатор пользователя

        Returns:
            Сумма баллов за достижения
        """
        try:
            achievements = await self.get_user_transactions(user_id, only_achievements=True)
            achievements_sum = 0

            for achievement in achievements:
                if achievement.type == "earn":
                    achievements_sum += achievement.amount

            return achievements_sum
        except Exception as e:
            logger.error(f"[БД] Ошибка вычисления суммы достижений пользователя {user_id}: {e}")
            return 0

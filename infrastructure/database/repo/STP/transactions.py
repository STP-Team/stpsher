import datetime
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
    kpi_extracted_at: Optional[datetime]


class TransactionRepo(BaseRepo):
    async def add_transaction(
        self,
        user_id: int,
        transaction_type: str,
        source_type: str,
        amount: int,
        source_id: Optional[int] = None,
        comment: Optional[str] = None,
        created_by: Optional[int] = None,
        kpi_extracted_at: Optional[datetime] = None,
    ) -> tuple[Transaction, int] | None:
        """
        Добавить новую транзакцию в БД

        Args:
            user_id: Идентификатор пользователя
            transaction_type: Тип операции: 'earn' или 'spend'
            source_type: Источник транзакции: 'achievement', 'product', 'casino', 'manual'
            amount: Количество баллов
            source_id: Идентификатор достижения или предмета (опционально)
            comment: Комментарий (опционально)
            created_by: ID администратора, создавшего транзакцию (опционально)
            kpi_extracted_at: Дата выгрузки KPI

        Returns:
            Объект Transaction или None в случае ошибки
        """
        try:
            transaction = Transaction(
                user_id=user_id,
                type=transaction_type,
                source_type=source_type,
                amount=amount,
                source_id=source_id,
                comment=comment,
                created_by=created_by,
                kpi_extracted_at=kpi_extracted_at,
            )

            self.session.add(transaction)
            await self.session.commit()
            await self.session.refresh(transaction)

            logger.info(
                f"[БД] Создана транзакция ID: {transaction.id} для пользователя {user_id}"
            )

            new_balance = await self.get_user_balance(transaction.user_id)
            return transaction, new_balance

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
                query = query.where(Transaction.source_type == "achievement")

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
        Вычислить сумму баллов за достижения пользователя (включая ручные транзакции)

        Args:
            user_id: Идентификатор пользователя

        Returns:
            Сумма баллов за достижения и ручные транзакции
        """
        try:
            query = select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.source_type.in_(["achievement", "manual"]),
                Transaction.type == "earn",
            )
            result = await self.session.execute(query)
            transactions = result.scalars().all()

            achievements_sum = sum(transaction.amount for transaction in transactions)
            return achievements_sum
        except Exception as e:
            logger.error(
                f"[БД] Ошибка вычисления суммы достижений пользователя {user_id}: {e}"
            )
            return 0

    async def get_group_transactions(self, head_name: str) -> Sequence[Transaction]:
        """
        Получить все транзакции группы по имени руководителя

        Args:
            head_name: ФИО руководителя

        Returns:
            Список транзакций всех участников группы
        """
        try:
            from infrastructure.database.models import Employee

            # Получаем всех участников группы
            group_members = await self.session.execute(
                select(Employee).where(Employee.head == head_name)
            )
            members = group_members.scalars().all()

            if not members:
                return []

            # Получаем user_id всех участников группы
            member_user_ids = [member.user_id for member in members if member.user_id]

            if not member_user_ids:
                return []

            # Получаем все транзакции участников группы
            query = select(Transaction).where(Transaction.user_id.in_(member_user_ids))
            query = query.order_by(Transaction.created_at.desc())
            result = await self.session.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(
                f"[БД] Ошибка получения транзакций группы для {head_name}: {e}"
            )
            return []

    async def get_heads_ranking_by_division(self, division: str) -> list[dict]:
        """
        Получить рейтинг руководителей по дивизиону на основе очков за текущий месяц с 1-го числа

        Args:
            division: Название дивизиона

        Returns:
            Список словарей с информацией о руководителях и их местах
        """
        try:
            from datetime import date, datetime

            from sqlalchemy import and_, func

            from infrastructure.database.models import Employee

            # Получаем начало текущего месяца (1-е число)
            current_date = datetime.now()
            month_start = date(current_date.year, current_date.month, 1)

            # Получаем всех руководителей указанного дивизиона
            heads_query = select(Employee).where(
                and_(
                    Employee.division == division,
                    Employee.role == 2,  # Роль руководителя
                )
            )
            heads_result = await self.session.execute(heads_query)
            heads = heads_result.scalars().all()

            if not heads:
                return []

            ranking = []

            for head in heads:
                # Получаем участников группы этого руководителя
                group_members = await self.session.execute(
                    select(Employee).where(Employee.head == head.fullname)
                )
                members = group_members.scalars().all()
                member_user_ids = [
                    member.user_id for member in members if member.user_id
                ]

                # Подсчитываем очки группы за текущий месяц с 1-го числа
                if member_user_ids:
                    points_query = select(func.sum(Transaction.amount)).where(
                        Transaction.user_id.in_(member_user_ids),
                        Transaction.type == "earn",
                        func.date(Transaction.created_at) >= month_start,
                    )
                    points_result = await self.session.execute(points_query)
                    points = points_result.scalar() or 0
                else:
                    points = 0

                ranking.append(
                    {
                        "head_name": head.fullname,
                        "username": head.username,
                        "points": points,
                        "group_size": len(members),
                    }
                )

            # Сортируем по убыванию очков
            ranking.sort(key=lambda x: x["points"], reverse=True)

            # Добавляем места
            for i, head_data in enumerate(ranking, 1):
                head_data["place"] = i

            return ranking

        except Exception as e:
            logger.error(
                f"[БД] Ошибка получения рейтинга руководителей для дивизиона {division}: {e}"
            )
            return []

    async def get_group_all_time_top_3(self, head_name: str) -> list[dict]:
        """
        Получить ТОП-3 участников группы по всем баллам за все время

        Args:
            head_name: ФИО руководителя

        Returns:
            Список словарей с информацией о топ-3 участниках группы за все время
        """
        try:
            from sqlalchemy import func

            from infrastructure.database.models import Employee

            # Получаем всех участников группы
            group_members = await self.session.execute(
                select(Employee).where(Employee.head == head_name)
            )
            members = group_members.scalars().all()

            if not members:
                return []

            # Получаем user_id всех участников группы
            member_user_ids = [member.user_id for member in members if member.user_id]

            if not member_user_ids:
                return []

            # Запрос для получения суммы очков каждого участника за все время
            all_time_stats_query = (
                select(
                    Transaction.user_id,
                    func.sum(Transaction.amount).label("all_time_points"),
                )
                .where(
                    Transaction.user_id.in_(member_user_ids), Transaction.type == "earn"
                )
                .group_by(Transaction.user_id)
            )

            all_time_stats_result = await self.session.execute(all_time_stats_query)
            all_time_stats = all_time_stats_result.all()

            # Сортируем по убыванию и берем ТОП-3
            top_3_all_time = sorted(
                all_time_stats, key=lambda x: x.all_time_points, reverse=True
            )[:3]

            # Формируем список ТОП-3 с именами
            top_3_list = []
            for user_stats in top_3_all_time:
                member = next(
                    (m for m in members if m.user_id == user_stats.user_id), None
                )
                if member:
                    top_3_list.append(
                        {
                            "name": member.fullname,
                            "username": member.username,
                            "points": user_stats.all_time_points,
                        }
                    )

            return top_3_list

        except Exception as e:
            logger.error(
                f"[БД] Ошибка получения ТОП-3 за все время для группы {head_name}: {e}"
            )
            return []

    async def get_group_stats_by_head(self, head_name: str) -> dict:
        """
        Получить статистику группы по имени руководителя

        Args:
            head_name: ФИО руководителя

        Returns:
            Словарь со статистикой группы
        """
        try:
            from datetime import datetime

            from sqlalchemy import func

            from infrastructure.database.models import Employee

            # Получаем всех участников группы
            group_members = await self.session.execute(
                select(Employee).where(Employee.head == head_name)
            )
            members = group_members.scalars().all()

            if not members:
                return {
                    "total_members": 0,
                    "total_points": 0,
                    "top_3_this_month": [],
                    "group_level": 0,
                }

            # Получаем user_id всех участников группы
            member_user_ids = [member.user_id for member in members if member.user_id]

            if not member_user_ids:
                return {
                    "total_members": len(members),
                    "total_points": 0,
                    "top_3_this_month": [],
                    "group_level": 0,
                }

            # Получаем общую сумму баллов группы (все транзакции типа earn)
            total_points_query = select(func.sum(Transaction.amount)).where(
                Transaction.user_id.in_(member_user_ids), Transaction.type == "earn"
            )
            total_points_result = await self.session.execute(total_points_query)
            total_points = total_points_result.scalar() or 0

            # Получаем ТОП-3 за текущий месяц с 1-го числа
            current_date = datetime.now()
            month_start = datetime(current_date.year, current_date.month, 1)

            # Запрос для получения суммы очков каждого участника за текущий месяц с 1-го числа
            month_stats_query = (
                select(
                    Transaction.user_id,
                    func.sum(Transaction.amount).label("month_points"),
                )
                .where(
                    Transaction.user_id.in_(member_user_ids),
                    Transaction.type == "earn",
                    Transaction.created_at >= month_start,
                )
                .group_by(Transaction.user_id)
            )

            month_stats_result = await self.session.execute(month_stats_query)
            month_stats = month_stats_result.all()

            # Сортируем по убыванию и берем ТОП-3
            top_3_month = sorted(
                month_stats, key=lambda x: x.month_points, reverse=True
            )[:3]

            # Формируем список ТОП-3 с именами
            top_3_list = []
            for user_stats in top_3_month:
                member = next(
                    (m for m in members if m.user_id == user_stats.user_id), None
                )
                if member:
                    top_3_list.append(
                        {
                            "name": member.fullname,
                            "username": member.username,
                            "points": user_stats.month_points,
                        }
                    )

            # Вычисляем средний уровень группы на основе общей суммы очков за достижения и ручные транзакции
            achievements_sum_query = select(func.sum(Transaction.amount)).where(
                Transaction.user_id.in_(member_user_ids),
                Transaction.type == "earn",
                Transaction.source_type.in_(["achievement", "manual"]),
            )
            achievements_sum_result = await self.session.execute(achievements_sum_query)
            achievements_sum = achievements_sum_result.scalar() or 0

            from tgbot.services.leveling import LevelingSystem

            avg_level = (
                LevelingSystem.calculate_level(achievements_sum // len(member_user_ids))
                if member_user_ids
                else 0
            )

            return {
                "total_members": len(members),
                "total_points": total_points,
                "top_3_this_month": top_3_list,
                "group_level": avg_level,
                "achievements_sum": achievements_sum,
            }

        except Exception as e:
            logger.error(
                f"[БД] Ошибка получения статистики группы для {head_name}: {e}"
            )
            return {
                "total_members": 0,
                "total_points": 0,
                "top_3_this_month": [],
                "group_level": 0,
            }

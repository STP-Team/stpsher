import logging
from typing import Optional, Sequence, TypedDict, Unpack

from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models.STP.user import User
from infrastructure.database.repo.base import BaseRepo

logger = logging.getLogger(__name__)


class RegisteredUserParams(TypedDict, total=False):
    """Доступные параметры для обновления пользователя в таблице RegisteredUsers."""

    user_id: int
    username: str | None
    division: str | None
    position: str | None
    fullname: str
    head: str | None
    email: str | None
    role: int


class UserRepo(BaseRepo):
    async def get_user(
        self,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        fullname: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Optional[User]:
        """
        Поиск пользователя в БД по фильтрам

        Args:
            user_id: Уникальный идентификатор пользователя Telegram
            username: Никнейм пользователя Telegram
            fullname: ФИО пользователя в БД
            email: Почта пользователя в БД

        Returns:
            Объект User или ничего
        """
        filters = []

        if user_id:
            filters.append(User.user_id == user_id)
        if username:
            filters.append(User.username == username)
        if fullname:
            filters.append(User.fullname == fullname)
        if email:
            filters.append(User.email == email)

        if not filters:
            raise ValueError("At least one parameter must be provided to get_user()")

        # Combine all filters using OR
        query = select(User).where(*filters)

        try:
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения пользователя: {e}")
            return None

    async def get_users(self) -> Sequence[User] | None:
        query = select(User)

        try:
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения списка пользователей: {e}")
            return None

    async def get_unauthorized_users(self, head_name: str = None) -> Sequence[User]:
        """
        Получить список неавторизованных пользователей
        Неавторизованные пользователи - те, у которых отсутствует user_id (не связан с Telegram)

        Args:
            head_name: Фильтр по имени руководителя (опционально)

        Returns:
            Список неавторизованных пользователей
        """
        # Основное условие - отсутствие user_id означает что пользователь не авторизован в Telegram
        base_conditions = [User.user_id.is_(None)]

        # Добавляем фильтр по руководителю если указан
        if head_name:
            base_conditions.append(User.head == head_name)

        query = select(User).where(*base_conditions).order_by(User.fullname)

        try:
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка получения списка неавторизованных пользователей: {e}"
            )
            return []

    async def update_user(
        self,
        user_id: int = None,
        **kwargs: Unpack[RegisteredUserParams],
    ) -> Optional[User]:
        select_stmt = select(User).where(User.user_id == user_id)

        result = await self.session.execute(select_stmt)
        user: User | None = result.scalar_one_or_none()

        # Если пользователь существует - обновляем его
        if user:
            for key, value in kwargs.items():
                setattr(user, key, value)
            await self.session.commit()

        return user

    async def get_users_by_fio_parts(
        self, fullname: str, limit: int = 10
    ) -> Sequence[User]:
        """
        Поиск пользователей по частичному совпадению ФИО
        Возвращает список пользователей для случаев, когда найдено несколько совпадений

        Args:
            fullname: Частичное или полное ФИО для поиска
            limit: Максимальное количество результатов

        Returns:
            Список объектов User
        """
        name_parts = fullname.strip().split()
        if not name_parts:
            return []

        # Создаём условия для каждой части имени
        like_conditions = []
        for part in name_parts:
            like_conditions.append(User.fullname.ilike(f"%{part}%"))

        # Все части должны присутствовать в ФИО (AND)
        query = select(User).where(and_(*like_conditions)).limit(limit)

        try:
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения пользователей по ФИО: {e}")
            return []

    async def get_users_by_head(self, head_name: str) -> Sequence[User]:
        """
        Получить всех пользователей с указанным руководителем

        Args:
            head_name: Имя руководителя

        Returns:
            Список пользователей с указанным руководителем
        """
        try:
            result = await self.session.execute(
                select(User).where(User.head == head_name).order_by(User.fullname)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(
                f"Ошибка получения пользователей по руководителю {head_name}: {e}"
            )
            return []

    async def get_admins(self) -> Sequence[User]:
        query = select(User).where(User.role == 10)

        try:
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения администраторов: {e}")
            return []

    async def delete_user(self, fullname: str) -> int:
        """
        Удаление ВСЕХ пользователей из БД по полному имени

        Args:
            fullname: Полное ФИО пользователя для удаления

        Returns:
            Количество удаленных пользователей
        """
        try:
            # Находим всех пользователей с таким ФИО
            query = select(User).where(User.fullname == fullname)
            result = await self.session.execute(query)
            users = result.scalars().all()

            deleted_count = 0
            for user in users:
                await self.session.delete(user)
                deleted_count += 1
                logger.info(
                    f"[БД] Пользователь {fullname} (ID: {user.user_id}) удален из базы данных"
                )

            if deleted_count > 0:
                await self.session.commit()
                logger.info(
                    f"[БД] Всего удалено {deleted_count} пользователей с ФИО {fullname}"
                )

            return deleted_count
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка удаления пользователей {fullname}: {e}")
            await self.session.rollback()
            return 0

from sqlalchemy import BIGINT, BOOLEAN, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base, TableNameMixin


class Employee(Base, TableNameMixin):
    """Модель, представляющая сущность сотрудника в БД.

    Args:
        id: Уникальный идентификатор сотрудника.
        user_id: Идентификатор чата с сотрудником в Telegram.
        username: username сотрудника в Telegram.
        division: Направление сотрудника (НТП/НЦК).
        position: Позиция/должность сотрудника.
        fullname: ФИО сотрудника.
        head: ФИО руководителя сотрудника.
        email: Email сотрудника.
        role: Роль сотрудника.
    """

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=True)
    username: Mapped[str] = mapped_column(Unicode, nullable=True)
    division: Mapped[str] = mapped_column(Unicode, nullable=True)
    position: Mapped[str] = mapped_column(Unicode, nullable=True)
    fullname: Mapped[str] = mapped_column(Unicode, nullable=False)
    head: Mapped[str] = mapped_column(Unicode, nullable=True)
    email: Mapped[str] = mapped_column(Unicode, nullable=True)
    role: Mapped[int] = mapped_column(BIGINT, nullable=False)
    is_trainee: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, default=True)
    is_casino_allowed: Mapped[bool] = mapped_column(BOOLEAN, nullable=False)

    def __repr__(self):
        return f"<Employee {self.id} {self.user_id} {self.username} {self.division} {self.position} {self.fullname} {self.head} {self.email} {self.role}>"

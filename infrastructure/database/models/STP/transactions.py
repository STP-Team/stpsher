from datetime import datetime
from typing import Optional

from sqlalchemy import TIMESTAMP, Enum, Integer, String
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from infrastructure.database.models.base import Base, TableNameMixin


class Transaction(Base, TableNameMixin):
    """
    Класс, представляющий сущность транзакции пользователя в БД.

    Attributes:
        id (Mapped[int]): Уникальный идентификатор транзакции.
        user_id (Mapped[int]): Идентификатор пользователя.
        type (Mapped[str]): Тип операции: начисление или списание.
        source_id (Mapped[Optional[int]]): Идентификатор достижения или предмета. Для manual или casino — NULL.
        source_type (Mapped[str]): Источник транзакции: achievement, product, casino, manual.
        amount (Mapped[int]): Количество баллов.
        comment (Mapped[Optional[str]]): Комментарий.
        created_by (Mapped[Optional[int]]): ID администратора, создавшего транзакцию.
        created_at (Mapped[Optional[datetime]]): Дата создания транзакции.

    Methods:
        __repr__(): Returns a string representation of the Transaction object.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.

    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=False)
    type: Mapped[str] = mapped_column(
        Enum("earn", "spend"),
        nullable=False,
        comment="Тип операции: начисление или списание",
    )
    source_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Идентификатор достижения или предмета. Для manual — NULL",
    )
    source_type: Mapped[str] = mapped_column(
        Enum("achievement", "product", "manual", "casino"),
        nullable=False,
        comment="Источник транзакции",
    )
    amount: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Количество баллов"
    )
    comment: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Комментарий"
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        BIGINT, nullable=True, comment="ID администратора, создавшего транзакцию"
    )
    kpi_extracted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        nullable=True,
        comment="Начальная дата выгружаемых показателей",
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        nullable=True,
        default=func.current_timestamp(),
        comment="Дата создания транзакции",
    )

    def __repr__(self):
        return f"<Transaction id={self.id} user_id={self.user_id} type={self.type} source_id={self.source_id} source_type={self.source_type} amount={self.amount} comment={self.comment} created_by={self.created_by} created_at={self.created_at}>"

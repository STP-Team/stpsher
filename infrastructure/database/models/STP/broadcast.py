from sqlalchemy import BIGINT, Enum, Text, TIMESTAMP, func, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional, List

from infrastructure.database.models.base import Base, TableNameMixin


class Broadcast(Base, TableNameMixin):
    """
    Модель, представляющая сущность рассылки в БД

    Attributes:
        id (Mapped[int]): Уникальный идентификатор рассылки.
        user_id (Mapped[int]): Идентификатор владельца рассылки.
        type (Mapped[str]): Тип рассылки: division или group.
        target (Mapped[str]): Конкретная цель рассылки: подразделение (НЦК, НТП1, НТП2) или выбранная группа.
        text (Mapped[str]): Текст рассылки.
        recipients (Mapped[Optional[List[int]]]): Список user_id, получивших рассылку.
        created_at (Mapped[TIMESTAMP]): Время создания рассылки.

    Methods:
        __repr__(): Returns a string representation of the Broadcast object.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.

    """

    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BIGINT, nullable=False, comment="Идентификатор владельца рассылки"
    )
    type: Mapped[str] = mapped_column(
        Enum("division", "group"),
        nullable=False,
        comment="Тип рассылки: division или group",
    )
    target: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Конкретная цель рассылки: подразделение (НЦК, НТП1, НТП2) или выбранная группа",
    )
    text: Mapped[str] = mapped_column(Text, nullable=False, comment="Текст рассылки")
    recipients: Mapped[Optional[List[int]]] = mapped_column(
        JSON, nullable=True, comment="Список user_id, получивших рассылку"
    )
    created_at: Mapped[TIMESTAMP] = mapped_column(
        TIMESTAMP, nullable=False, server_default=func.current_timestamp()
    )

    def __repr__(self):
        return f"<Broadcast {self.id} user_id={self.user_id} type={self.type} target={self.target} recipients={len(self.recipients or [])} created_at={self.created_at}>"

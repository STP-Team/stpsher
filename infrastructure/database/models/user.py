from sqlalchemy import BIGINT, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TableNameMixin


class User(Base, TableNameMixin):
    """
    Модель, представляющая сущность пользователя в БД

    Attributes:
        id (Mapped[int]): Уникальный идентификатор пользователя.
        chat_id (Mapped[Optional[str]]): Идентификатор чата с пользователем в Telegram.
        username (Mapped[str]): username пользователя в Telegram.
        division (MappedOptional[str]): Направление пользователя (НТП/НЦК).
        position (Mapped[str]): Позиция/должность пользователя.
        fullname (Mapped[str]): ФИО пользователя.
        head (Mapped[str]): ФИО руководителя пользователя.
        email (Mapped[str]): email пользователя.
        role (Mapped[int]): Роль пользователя в БД.

    Methods:
        __repr__(): Returns a string representation of the User object.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.

    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BIGINT)
    username: Mapped[str] = mapped_column(Unicode, nullable=True)
    division: Mapped[str] = mapped_column(Unicode)
    position: Mapped[str] = mapped_column(Unicode)
    fullname: Mapped[str] = mapped_column(Unicode)
    head: Mapped[str] = mapped_column(Unicode)
    email: Mapped[str] = mapped_column(Unicode)
    role: Mapped[int] = mapped_column(BIGINT)

    def __repr__(self):
        return f"<User {self.id} {self.chat_id} {self.username} {self.division} {self.position} {self.fullname} {self.head} {self.email} {self.role}>"

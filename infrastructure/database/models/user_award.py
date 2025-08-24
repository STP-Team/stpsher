from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.dialects.mysql import BIGINT, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TableNameMixin


class UserAward(Base, TableNameMixin):
    """
    Класс, представляющий сущность награды пользователя в БД.

    Attributes:
        id (Mapped[int]): Уникальный идентификатор пользователя.
        user_id (Mapped[int]): Идентификатор пользователя Telegram, запросившего награду.
        award_id (Mapped[int]): Идентификатор награды в таблице awards.
        comment (Mapped[str]): Комментарий пользователя к поданной награде.
        usage_count (Mapped[int]): Кол-во использований награды.
        bought_at (Mapped[datetime]): Время приобретения награды.
        updated_at (Mapped[datetime]): Время подтверждения награды.
        updated_by_user_id (Mapped[int]): Идентификатор пользователя Telegram, активировавшего награду

    Methods:
        __repr__(): Returns a string representation of the User object.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.

    """

    __tablename__ = "users_awards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=True)
    award_id: Mapped[int] = mapped_column(VARCHAR(255), nullable=False)
    comment: Mapped[str] = mapped_column(VARCHAR, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bought_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=datetime.now
    )
    updated_by_user_id: Mapped[int] = mapped_column(BIGINT, nullable=True)
    status: Mapped[str] = mapped_column(VARCHAR(10), nullable=False, default="waiting")

    def __repr__(self):
        return f"<UserAward {self.id} {self.user_id} {self.award_id} {self.comment} {self.usage_count} {self.bought_at} {self.updated_at} {self.updated_by_user_id} {self.status}>"

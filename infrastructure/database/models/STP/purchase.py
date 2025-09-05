from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.dialects.mysql import BIGINT, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base, TableNameMixin


class Purchase(Base, TableNameMixin):
    """
    Класс, представляющий сущность покупки пользователя в БД.

    Attributes:
        id (Mapped[int]): Уникальный идентификатор пользователя.
        user_id (Mapped[int]): Идентификатор пользователя, который приобрел предмет.
        product_id (Mapped[int]): Идентификатор предмета в таблице products.
        comment (Mapped[str]): Комментарий пользователя к поданному предмету.
        usage_count (Mapped[int]): Кол-во использований предмета.
        bought_at (Mapped[datetime]): Время приобретения предмета.
        updated_at (Mapped[datetime]): Время подтверждения предмета.
        updated_by_user_id (Mapped[int]): Идентификатор пользователя Telegram, активировавшего покупку

    Methods:
        __repr__(): Returns a string representation of the User object.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.

    """

    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=True)
    product_id: Mapped[int] = mapped_column(VARCHAR(255), nullable=False)
    comment: Mapped[str] = mapped_column(VARCHAR, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bought_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=datetime.now
    )
    updated_by_user_id: Mapped[int] = mapped_column(BIGINT, nullable=True)
    status: Mapped[str] = mapped_column(VARCHAR(10), nullable=False, default="stored")

    def __repr__(self):
        return f"<ProductUsage {self.id} {self.user_id} {self.product_id} {self.comment} {self.usage_count} {self.bought_at} {self.updated_at} {self.updated_by_user_id} {self.status}>"

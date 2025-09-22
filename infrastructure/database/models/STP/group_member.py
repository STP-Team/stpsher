from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base, TableNameMixin


class GroupMember(Base, TableNameMixin):
    """
    Класс, представляющий сущность участника группы в БД.

    Attributes:
        group_id (Mapped[int]): Идентификатор группы Telegram.
        member_id (Mapped[int]): Идентификатор участника Telegram.
        added_at (Mapped[datetime]): Время добавления в группу.

    Methods:
        __repr__(): Returns a string representation of the GroupMember object.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.

    """

    __tablename__ = "group_members"

    group_id: Mapped[int] = mapped_column(
        BIGINT,
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        primary_key=True,
        comment="Идентификатор группы Telegram",
    )
    member_id: Mapped[int] = mapped_column(
        BIGINT, primary_key=True, comment="Идентификатор участника Telegram"
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        comment="Время добавления в группу",
    )

    def __repr__(self):
        return f"<GroupMember group_id={self.group_id} member_id={self.member_id}>"

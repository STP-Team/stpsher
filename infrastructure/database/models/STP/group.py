from sqlalchemy import JSON, Boolean
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base, TableNameMixin


class Group(Base, TableNameMixin):
    """
    Класс, представляющий сущность группы в БД.

    Attributes:
        group_id (Mapped[int]): Идентификатор группы Telegram.
        invited_by (Mapped[int]): Идентификатор Telegram пригласившего.
        remove_unemployed (Mapped[bool]): Удалять уволенных сотрудников из группы.

    Methods:
        __repr__(): Returns a string representation of the Group object.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.

    """

    __tablename__ = "groups"

    group_id: Mapped[int] = mapped_column(
        BIGINT, primary_key=True, comment="Идентификатор группы Telegram"
    )
    invited_by: Mapped[int] = mapped_column(
        BIGINT, nullable=False, comment="Идентификатор Telegram пригласившего"
    )
    remove_unemployed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="Удалять уволенных сотрудников из группы",
        default=0,
    )
    is_casino_allowed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="Возможность использовать казино в группе",
        default=1,
    )
    new_user_notify: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="Уведомлять о новых вступивших участниках в группу",
        default=1,
    )
    allowed_roles: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        comment="Список разрешенных ролей для доступа к группе",
        default=[],
    )
    service_messages: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        comment="Список сервисных сообщений на удаление",
        default=[],
    )

    def __repr__(self):
        return f"<Group group_id={self.group_id} invited_by={self.invited_by}>"

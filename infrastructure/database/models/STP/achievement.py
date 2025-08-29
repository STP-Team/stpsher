from sqlalchemy import Integer
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base, TableNameMixin


class Achievement(Base, TableNameMixin):
    """
    Класс, представляющий сущность достижения в БД.

    Attributes:
        id (Mapped[int]): Уникальный идентификатор пользователя.
        name (Mapped[str]): Название достижения.
        description (Mapped[int]): Описание достижения.
        division (Mapped[str]): Направление для получения достижения.
        kpi (Mapped[str]): Показатели для получения достижения.
        reward (Mapped[str]): Награда за достижение в баллах.
        position (Mapped[str]): Позиция специалиста для получения достижения.

    Methods:
        __repr__(): Returns a string representation of the User object.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.

    """

    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(VARCHAR(30), nullable=False)
    description: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    division: Mapped[str] = mapped_column(VARCHAR(3), nullable=False)
    kpi: Mapped[str] = mapped_column(VARCHAR(3), nullable=False)
    reward: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[str] = mapped_column(VARCHAR(31), nullable=False)
    period: Mapped[str] = mapped_column(VARCHAR(1), nullable=False)

    def __repr__(self):
        return (
            f"<Achievement {self.id} {self.name} {self.description}"
            f"{self.division} {self.kpi} {self.reward} {self.position} {self.period}>"
        )

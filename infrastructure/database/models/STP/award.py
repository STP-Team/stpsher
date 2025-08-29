from sqlalchemy import Integer
from sqlalchemy.dialects.mysql import VARCHAR, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base, TableNameMixin


class Award(Base, TableNameMixin):
    """
    Класс, представляющий сущность награды в БД.

    Attributes:
        id (Mapped[int]): Уникальный идентификатор пользователя.
        name (Mapped[str]): Название награды.
        description (Mapped[int]): Стоимость награды.
        cost (Mapped[str]): Роль для взаимодействия.
        count (Mapped[int]): Кол-во доступных использований награды после приобретения.
        manager_role (Mapped[str]): Описание награды.
        shift_dependent (Mapped[bool]): Зависимость применения награды от наличия смены.

    Methods:
        __repr__(): Returns a string representation of the User object.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.

    """

    __tablename__ = "awards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    description: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    division: Mapped[str] = mapped_column(VARCHAR(3), nullable=False)
    cost: Mapped[int] = mapped_column(Integer, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    manager_role: Mapped[str] = mapped_column(Integer, nullable=False)
    shift_dependent: Mapped[bool] = mapped_column(TINYINT, default=True, nullable=False)

    def __repr__(self):
        return (
            f"<Award {self.id} {self.name} {self.description}"
            f"{self.division} {self.cost} {self.count} {self.manager_role} {self.shift_dependent}>"
        )

from sqlalchemy import JSON, Integer
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base, TableNameMixin


class Product(Base, TableNameMixin):
    """
    Класс, представляющий сущность предмета в БД.

    Attributes:
        id (Mapped[int]): Уникальный идентификатор пользователя.
        name (Mapped[str]): Название предмета.
        description (Mapped[int]): Описание предмета.
        cost (Mapped[str]): Стоимость предмета.
        count (Mapped[int]): Кол-во доступных использований предмета после приобретения.
        manager_role (Mapped[int]): Роль для взаимодействия.

    Methods:
        __repr__(): Returns a string representation of the User object.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.

    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    description: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    division: Mapped[str] = mapped_column(VARCHAR(3), nullable=False)
    cost: Mapped[int] = mapped_column(Integer, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    activate_days: Mapped[list] = mapped_column(JSON, nullable=True)
    manager_role: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self):
        return (
            f"<Product {self.id} {self.name} {self.description}"
            f"{self.division} {self.cost} {self.count} {self.manager_role}>"
        )

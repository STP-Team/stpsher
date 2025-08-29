from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.dialects.mysql import BIGINT, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base, TableNameMixin


class UserAchievement(Base, TableNameMixin):
    """
    Класс, представляющий сущность достижения пользователя в БД.

    Attributes:
        id (Mapped[int]): Уникальный идентификатор пользователя.
        user_id (Mapped[int]): Идентификатор пользователя Telegram, запросившего награду.
        achievement_id (Mapped[int]): Идентификатор награды в таблице achievements.
        achieved_kpi (Mapped[str]): Достигнутый показатель KPI при получении достижения.
        achieved_at (Mapped[datetime]): Время получения достижения.

    Methods:
        __repr__(): Returns a string representation of the User object.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.

    """

    __tablename__ = "users_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=True)
    achievement_id: Mapped[int] = mapped_column(Integer, nullable=True)
    achieved_kpi: Mapped[str] = mapped_column(VARCHAR(255), nullable=True)
    achieved_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self):
        return f"<UserAchievement {self.id} {self.user_id} {self.achievement_id} {self.achieved_kpi} {self.achieved_at}>"

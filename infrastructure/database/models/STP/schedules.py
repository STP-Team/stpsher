from datetime import datetime
from typing import Optional
from sqlalchemy import BIGINT, Integer, String, Text, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base, TableNameMixin


class Schedules(Base, TableNameMixin):
    """
    Модель, представляющая сущность лога расписания в БД

    Attributes:
        id (Mapped[int]): Уникальный идентификатор записи.
        file_id (Mapped[str]): Идентификатор Telegram загруженного файла.
        file_name (Mapped[Optional[str]]): Название загруженного файла.
        file_size (Mapped[Optional[int]]): Размер файла в байтах.
        uploaded_by_user_id (Mapped[int]): Идентификатор пользователя, загрузившего файл.
        uploaded_at (Mapped[datetime]): Время загрузки файла.

    Methods:
        __repr__(): Возвращает строковое представление объекта ScheduleLog.

    Inherited Attributes:
        Наследует от Base и TableNameMixin, которые предоставляют дополнительный функционал.
    """

    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Идентификатор Telegram загруженного файла"
    )
    file_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Название загруженного файла"
    )
    file_size: Mapped[Optional[int]] = mapped_column(
        BIGINT, nullable=True, comment="Размер файла в байтах"
    )
    uploaded_by_user_id: Mapped[int] = mapped_column(BIGINT, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=func.current_timestamp()
    )

    def __repr__(self):
        return (
            f"<ScheduleLog id={self.id} file_id={self.file_id} file_name={self.file_name} "
            f"file_size={self.file_size} uploaded_by_user_id={self.uploaded_by_user_id} uploaded_at={self.uploaded_at}>"
        )
